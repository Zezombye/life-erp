#!/usr/bin/python3

import os
import json
import time
import unicodedata
import re
import googleapiclient.discovery
from google_auth_oauthlib.flow import InstalledAppFlow
from collections import defaultdict
import google.oauth2

class Youtube():

    def __init__(self):
        clientSecretsFile = "c:/users/zezombye/yt_client_secret.json"

        try:
            credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(clientSecretsFile)
        except (ValueError) as e: # first run with new secret.json
            flow = InstalledAppFlow.from_client_secrets_file(clientSecretsFile, ["https://www.googleapis.com/auth/youtube"])
            credentials = flow.run_local_server(port=0)
            with open(clientSecretsFile, 'w+') as file:
                file.write(credentials.to_json())
        self.youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

        self.BEST_OF_PLAYLIST_ID = "PLDS8MSVtwiPYVvz3D43_gWJGfXKv8ZTxg"
        self.WL_ID = "PLK5yrmOBPizjuP7IUTU3HcCo3YJ3L96Dz"


    def normalize(self, text):

        text = text.lower()
        # Remove accents
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')

        text = text.replace("'", "").replace(".", "")
        text = text.replace(" & ", " and ")

        # Remove content inside parentheses
        text = re.sub(r'\(\(.*?\)\)', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'\[.*?\]', '', text)

        #"Artist: song" -> "Artist - song"
        #We don't care if it also affects the title, it leads to better sorting
        text = re.sub(r':', ' - ', text)
        # Replace punctuation with spaces
        text = re.sub(r'[^\w\s-]', ' ', text)

        # Replace multiple spaces with a single space and trim
        text = re.sub(r'\s+', ' ', text).strip()

        return text


    def getSongHash(self, video):
        #Used to detect duplicate songs + sorting

        title = self.normalize(video["title"])
        if video["description"].endswith("\n\nAuto-generated by YouTube.") or video["channelId"] in [
            "UCus8EVJ7Oc9zINhs-fg8l1Q", #Turbo
            "UC9EzN5XNxhxqHZevM9kSuaw", #Approaching Nirvana
        ]:
            #Official music video
            artist = self.normalize(video["channelName"]).replace(" - topic", "")
            if artist == "approachingnirvana":
                artist = "approaching nirvana"
            if artist == "planetsaxon":
                artist = "saxon"
            #Sometimes the official music videos have the artist at the end
            if title.endswith(" - "+artist):
                title = title.replace(" - "+artist, "")

            title = artist + " - " + title

        return title.title()


    def fetch_playlist(self, playlist_id):
        print("Fetching playlist '%s'" % (playlist_id))
        playlist_items = []
        next_page_token = None

        while len(playlist_items) < 9999999:
            request = self.youtube.playlistItems().list(
                part="snippet,contentDetails,status,id",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
            playlist_items.extend(response['items'])
            next_page_token = response.get('nextPageToken')
            print("Got %s video(s)" % (len(playlist_items)))
            if not next_page_token:
                break


        with open("debug/yt_playlist.json", "w+", encoding="utf-8") as f:
            f.write(json.dumps(playlist_items, indent=4, ensure_ascii=False))

        return [{
            "publishedAt": i["snippet"]["publishedAt"],
            "title": i["snippet"]["title"],
            "description": i["snippet"]["description"],
            "channelName": i["snippet"]["videoOwnerChannelTitle"],
            "channelId": i["snippet"]["videoOwnerChannelId"],
            "id": i["snippet"]["resourceId"]["videoId"],
            "playlistitem_id": i["id"],
            "position": i["snippet"]["position"],
        } for i in playlist_items]


    def compare_playlists(self, new_playlist, existing_playlist_path):
        """Compare new playlist with an existing playlist."""
        if not os.path.exists(existing_playlist_path):
            return [], new_playlist, []

        with open(existing_playlist_path, 'r', encoding='utf-8') as f:
            old_playlist = json.load(f)

        old_video_ids = {item['snippet']['resourceId']['videoId'] for item in old_playlist}
        new_video_ids = {item['snippet']['resourceId']['videoId'] for item in new_playlist}

        removed_videos = old_video_ids - new_video_ids

        return removed_videos, new_playlist, []


    def sort_playlist(self, playlist_id, playlist_items):
        print(f"Sorting playlist with {len(playlist_items)} videos...")

        sorted_playlist = sorted(playlist_items, key=lambda x: self.getSongHash(x)+"["+x["id"]+"]")

        for i in range(len(sorted_playlist) - 1, -1, -1):
            if playlist_items[i]["id"] != sorted_playlist[i]["id"]:

                for index, item in enumerate(playlist_items):
                    if item["id"] == sorted_playlist[i]["id"]:
                        video_to_move = item
                        video_to_move_idx = index
                        break
                else:
                    raise ValueError("Could not find video %s" % (sorted_playlist[i]))

                print(f"Moving video {video_to_move["id"]} ({self.getSongHash(video_to_move)}) from position {video_to_move_idx} to {i}")

                # Update the video position using the YouTube API
                while True:
                    try:
                        time.sleep(1)
                        self.youtube.playlistItems().update(
                            part="snippet",
                            body={
                                "id": video_to_move['playlistitem_id'],
                                "snippet": {
                                    "playlistId": playlist_id,
                                    "position": i,
                                    "resourceId": {
                                        "kind": "youtube#video",
                                        "videoId": video_to_move['id'],
                                    }
                                }
                            }
                        ).execute()
                        break
                    except Exception as e:
                        print(e)
                        if "'SERVICE_UNAVAILABLE'" not in str(e):
                            raise


                playlist_items.pop(video_to_move_idx)
                playlist_items.insert(i, video_to_move)


        print("Playlist sorted successfully!")

        for i in range(len(sorted_playlist)):
            sorted_playlist[i]["position"] = i

        return sorted_playlist






    def main(self):



        playlist_id = self.BEST_OF_PLAYLIST_ID

        # Fetch the playlist
        print("Fetching playlist...")
        videos = self.fetch_playlist(playlist_id)

        print("Fetching video details")

        videoDetails = []
        for i in range(0, len(videos), 50):

            response = self.youtube.videos().list(
                part="contentDetails,status",
                id=",".join([v["id"] for v in videos[i:i+50]]),
            ).execute()
            videoDetails.extend(response['items'])
            print("Got %s video(s)" % (len(videoDetails)))


        with open("debug/yt_video_details.json", "w+", encoding="utf-8") as f:
            f.write(json.dumps(videoDetails, indent=4, ensure_ascii=False))


        songHashes = set()
        duplicatedSongHashes = set()
        for video in videos:
            if self.getSongHash(video) in songHashes:
                duplicatedSongHashes.add(self.getSongHash(video))
            else:
                songHashes.add(self.getSongHash(video))

        for video in videoDetails:
            if video["status"]["privacyStatus"] != "public" or "regionRestriction" in video["contentDetails"] and ("allowed" in video["contentDetails"]["regionRestriction"] and "FR" not in video["contentDetails"]["regionRestriction"]["allowed"] or "blocked" in video["contentDetails"]["regionRestriction"] and "FR" in video["contentDetails"]["regionRestriction"]["blocked"]):
                videoInPlaylist = [v for v in videos if v["id"] == video["id"]][0]
                if self.getSongHash(videoInPlaylist) in duplicatedSongHashes:
                    print("Video %s (%s) is no longer available but is a duplicate, removing it" % (videoInPlaylist["id"], videoInPlaylist["title"]))
                    self.youtube.playlistItems().delete(id=videoInPlaylist['playlistitem_id']).execute()
                    videos = [v for v in videos if v["id"] != videoInPlaylist["id"]]

                else:
                    print("Video %s (%s) is no longer available, put it again in the playlist for it to be removed" % (videoInPlaylist["id"], videoInPlaylist["title"]))


        uniqueVideos = {}
        for video in videos:
            videoHash = self.getSongHash(video)
            if videoHash in uniqueVideos:
                print("Duplicate detected: video at pos %s with id %s '%s' is the same as video at pos %s with id %s '%s'" % (video["position"], video["id"], video["title"], uniqueVideos[videoHash]["position"], uniqueVideos[videoHash]["id"], uniqueVideos[videoHash]["title"]))
            else:
                uniqueVideos[videoHash] = video


        artistCounts = {}
        for video in videos:
            artist = self.getSongHash(video).split(" - ")[0]
            if artist in artistCounts:
                artistCounts[artist] += 1
            else:
                artistCounts[artist] = 1

        artistCounts = {k: v for k, v in sorted(artistCounts.items(), key=lambda item: -item[1])}
        #for artist, artistCount in artistCounts.items():
        #    print(artist, artistCount)

        videos = self.sort_playlist(playlist_id, videos)

        #for video in videos:
        #    print(video["position"], self.getSongHash(video))


        with open("bestof.json", "w+", encoding="utf-8") as f:
            f.write(json.dumps(videos, indent=4, ensure_ascii=False))

        return

        # Compare with existing playlist if exists
        print("Comparing with existing playlist...")
        removed_videos, _, _ = self.compare_playlists(videos, output_path)

        if removed_videos:
            print("Removed videos:")
            for video_id in removed_videos:
                print(f"Video ID: {video_id}")

        # Find duplicates and sort
        print("Checking for duplicates and sorting...")
        duplicates, sorted_playlist = self.find_duplicates_and_sort(videos)

        if duplicates:
            print("\nDuplicate songs found:")
            for dup_group in duplicates:
                print("\nDuplicate group:")
                for idx, title in dup_group:
                    print(f"Position: {idx}, Title: {title}")
        else:
            print("No duplicates found.")

        # Save sorted playlist to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_playlist, f, indent=2)

        print(f"\nSorted playlist saved to {output_path}")

if __name__ == "__main__":
    youtube = Youtube()
    youtube.main()
