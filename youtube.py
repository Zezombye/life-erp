#!/usr/bin/python3

import os
import json
import subprocess
import sys
import time
import unicodedata
import re
import googleapiclient.discovery
from google_auth_oauthlib.flow import InstalledAppFlow
from collections import defaultdict
import google.oauth2
import utils
import config

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
        self.ytApiClient = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
        self.BACKUP_DIR = config.BACKUP_DIR+"/youtube/"
        self.REGION_CODE = "FR"


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

    def isAutoGeneratedVideo(self, video):
        return video["description"].endswith("\n\nAuto-generated by YouTube.")


    def getSongHash(self, video):
        #Used to detect duplicate songs + sorting

        title = self.normalize(video["title"])
        if self.isAutoGeneratedVideo(video) or video["channelId"] in [
            "UCus8EVJ7Oc9zINhs-fg8l1Q", #Turbo
            "UC9EzN5XNxhxqHZevM9kSuaw", #Approaching Nirvana
            "UCZU9T1ceaOgwfLRq7OKFU4Q", #Linkin Park
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

    def get_playlist_info(self, playlistId):
        print("Getting info of playlist '%s'" % (playlistId))
        try:
            r = self.ytApiClient.playlists().list(
                part="snippet,contentDetails,id,player,status",
                id=playlistId,
                maxResults=25
            ).execute()

            playlistInfo = r["items"][0]
            return {
                "id": playlistInfo["id"],
                "channelId": playlistInfo["snippet"]["channelId"],
                "channelName": playlistInfo["snippet"]["channelTitle"],
                "title": playlistInfo["snippet"]["title"],
                "description": playlistInfo["snippet"]["description"],
            }
        except Exception as e:
            print("Could not get info of playlist '%s': %s" % (playlistId, e))
            raise

    def get_playlist_videos(self, playlist_id, with_details=True):
        print("Fetching playlist '%s'" % (playlist_id))
        playlist_items = []
        total_items_count = None
        next_page_token = None

        while len(playlist_items) < 9999999:
            request = self.ytApiClient.playlistItems().list(
                part="snippet,contentDetails,status,id",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
            playlist_items.extend(response['items'])
            next_page_token = response.get('nextPageToken')
            total_items_count = response["pageInfo"]["totalResults"]
            #print("Got %s/%s video(s)" % (len(playlist_items), total_items_count))
            if not next_page_token:
                break


        with open("debug/yt_playlist.json", "w+", encoding="utf-8") as f:
            f.write(json.dumps(playlist_items, indent=4, ensure_ascii=False))

        videos = [{
            "publishedAt": i["snippet"]["publishedAt"],
            "title": i["snippet"]["title"],
            "description": i["snippet"]["description"],
            "channelName": i["snippet"].get("videoOwnerChannelTitle") or "null",
            "channelId": i["snippet"].get("videoOwnerChannelId") or "null",
            "id": i["snippet"]["resourceId"]["videoId"],
            "playlistitem_id": i["id"],
            "position": i["snippet"]["position"],
            "isAvailable": not(i["snippet"]["title"] == "Private video" and i["status"]["privacyStatus"] == "private"),
        } for i in playlist_items]

        if with_details:
            print("Fetching video details")

            videoDetails = []
            for i in range(0, len(videos), 50):

                response = self.ytApiClient.videos().list(
                    part="contentDetails,status",
                    id=",".join([v["id"] for v in videos[i:i+50]]),
                ).execute()
                videoDetails.extend(response['items'])
                #print("Got %s/%s video(s)" % (len(videoDetails), total_items_count))

            with open("debug/yt_video_details.json", "w+", encoding="utf-8") as f:
                f.write(json.dumps(videoDetails, indent=4, ensure_ascii=False))

            for videoDetail in videoDetails:
                matchingVideo = [v for v in videos if v["id"] == videoDetail["id"]][0]
                if "regionRestriction" in videoDetail["contentDetails"] and (
                    "allowed" in videoDetail["contentDetails"]["regionRestriction"] and self.REGION_CODE not in videoDetail["contentDetails"]["regionRestriction"]["allowed"]
                    or "blocked" in videoDetail["contentDetails"]["regionRestriction"] and self.REGION_CODE in videoDetail["contentDetails"]["regionRestriction"]["blocked"]
                ):
                    matchingVideo["isAvailable"] = False

        for video in videos:
            video["songHash"] = self.getSongHash(video)

        return videos


    def download_video(self, videoId, destinationDir, playlistIndex=None, audioOnly=False):
        if not utils.isValidYtVideoId(videoId):
            raise ValueError("Invalid video id '%s'" % (videoId))

        for file in os.listdir(destinationDir):
            if any([x == videoId for x in file.split(utils.SEPARATOR)[:2]]):
                #print("Video '%s' is already downloaded" % (videoId))
                return


        print("Downloading video '%s'" % (videoId))
        try:
            #Note: max resolution is 720p to not take gigabytes of data for podcasts. This is for backups, we don't need high resolution
            #Going from 1080p to 720p is up to 80% reduction in size

            command = 'yt-dlp "https://www.youtube.com/watch?v='+videoId+'" --abort-on-error --embed-metadata --trim-filenames 250'

            playlistIndexStr = ("%02d"%(playlistIndex)+utils.SEPARATOR if playlistIndex is not None else "")
            if audioOnly:
                command += ' -x --split-chapters'
                outputFormat = f' -o "{playlistIndexStr}%(id)s{utils.SEPARATOR}%(uploader).100B{utils.SEPARATOR}%(title).200B.%(ext)s"'
                outputFormat += f' -o "chapter:{playlistIndexStr}%(id)s{utils.SEPARATOR}%(uploader).100B{utils.SEPARATOR}%(title).200B/%(section_number).02d. %(section_title).200B.%(ext)s"'
                #outputFormat = f"%(chapters&{playlistIndexStr}{utils.SEPARATOR}%(id)s{utils.SEPARATOR}%(uploader).100B/%(section_number).02d{utils.SEPARATOR}%(section_title).200B.%(ext)s|{playlistIndexStr}%(id)s{utils.SEPARATOR}%(uploader).100B{utils.SEPARATOR}%(title).200B.%(ext)s)s"
            else:
                #--embed-thumbnail cannot be used for audio if splitting chapters, and we don't know ahead of time if the video has chapters
                #https://github.com/yt-dlp/yt-dlp/issues/6225
                command += ' --compat-options no-keep-subs --embed-info-json --embed-thumbnail --embed-subs --write-subs --write-auto-subs --sub-lang "en.*",en,en-US -S "res:720" --merge-output-format mkv'
                #01 | [id] | uploader | title.mp4
                outputFormat = f' -o "{playlistIndexStr}%(id)s{utils.SEPARATOR}%(uploader).100B{utils.SEPARATOR}%(title).200B.%(ext)s"'

            command += " " + outputFormat

            subprocess.check_output(command, cwd=destinationDir)
        except subprocess.CalledProcessError as e:
            print("Could not download video '%s':\n%s" % (videoId, e.output.decode()))
            raise

        #Sadly there is no option to delete original file after splitting on chapters, so we have to check if a dir was created, if so delete files matching the video id.
        #https://github.com/yt-dlp/yt-dlp/issues/4686
        hasDirBeenCreated = False
        for file in os.listdir(destinationDir):
            if not os.path.isdir(destinationDir+"/"+file):
                continue
            if any([x == videoId for x in file.split(utils.SEPARATOR)[:2]]):
                #print("Video '%s' has been split by chapters" % (videoId))
                hasDirBeenCreated = True
        if hasDirBeenCreated:
            for file in os.listdir(destinationDir):
                if not os.path.isdir(destinationDir+"/"+file):
                    if any([x == videoId for x in file.split(utils.SEPARATOR)[:2]]):
                        #print("Removing file '%s'" % (file))
                        os.remove(destinationDir+"/"+file)




    def download_playlist(self, playlistId, destinationDir=None, audioOnly=False):
        if destinationDir is None:
            destinationDir = self.BACKUP_DIR

        if not utils.isValidYtPlaylistId(playlistId):
            raise ValueError("Invalid playlist id '%s'" % (playlistId))

        base32768id = utils.ytPlaylistIdToBase32768(playlistId)
        playlistInfo = self.get_playlist_info(playlistId)

        print("Downloading playlist '%s' (%s)" % (playlistId, playlistInfo["title"]))

        playlistDir = utils.sanitizeForWindowsFilename(playlistInfo["title"]+utils.SEPARATOR+base32768id)

        for file in os.listdir(destinationDir):
            if file.endswith(utils.SEPARATOR+base32768id) and file != playlistDir:
                print("Renaming dir '%s' for playlist '%s'" % (file, playlistInfo["title"]))
                os.rename(os.path.join(destinationDir, file), os.path.join(destinationDir, playlistDir))

        os.makedirs(os.path.join(destinationDir, playlistDir), exist_ok=True)

        videos = self.get_playlist_videos(playlistId)
        for video in videos:
            if not video["isAvailable"]:
                print("Skipping downloading unavailable video '%s' (%s)" % (video["id"], video["title"]))
                continue
            if self.isAutoGeneratedVideo(video):
                #Official song so very probably possible to find elsewhere anyways
                continue
            try:
                self.download_video(video["id"], os.path.join(destinationDir, playlistDir), video["position"]+1, audioOnly=audioOnly)
            except Exception as e:
                print("Could not download video '%s' (%s)" % (video["id"], video["title"]), file=sys.stderr)
                #Do not raise, it was very probably a video which is no longer available, which is why we back up :)



    def sort_playlist(self, playlist_id, playlist_items):
        print(f"Sorting playlist with {len(playlist_items)} videos...")

        sorted_playlist = sorted(playlist_items, key=lambda x: x["songHash"]+" ["+x["id"]+"]")

        for i in range(len(sorted_playlist) - 1, -1, -1):
            if playlist_items[i]["id"] != sorted_playlist[i]["id"]:

                for index, item in enumerate(playlist_items):
                    if item["id"] == sorted_playlist[i]["id"]:
                        video_to_move = item
                        video_to_move_idx = index
                        break
                else:
                    raise ValueError("Could not find video %s" % (sorted_playlist[i]))

                print(f"Moving video {video_to_move["id"]} ({video_to_move["songHash"]}) from position {video_to_move_idx} to {i}")

                # Update the video position using the YouTube API
                while True:
                    try:
                        time.sleep(1)
                        self.ytApiClient.playlistItems().update(
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


    def delete_playlist_item(self, playlistItemId):
        self.ytApiClient.playlistItems().delete(id=playlistItemId).execute()


    def main(self):

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
    youtube.download_video("1UhCACcsWHQ", "D:/bkp/youtube/", 12, audioOnly=True)
    youtube.download_video("pJvduG0E628", "D:/bkp/youtube/", 12, audioOnly=True)
    #youtube.main()
