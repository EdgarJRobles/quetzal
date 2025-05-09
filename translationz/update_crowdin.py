#!/usr/bin/env python3

# SPDX-License-Identifier: LGPL-2.1-or-later
# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2015 Yorik van Havre <yorik@uncreated.net>              *
# *   Copyright (c) 2021 Benjamin Nauck <benjamin@nauck.se>                 *
# *   Copyright (c) 2021 Mattias Pierre <github@mattiaspierre.com>          *
# *                                                                         *
# *   This file is part of FreeCAD.                                         *
# *                                                                         *
# *   FreeCAD is free software: you can redistribute it and/or modify it    *
# *   under the terms of the GNU Lesser General Public License as           *
# *   published by the Free Software Foundation, either version 2.1 of the  *
# *   License, or (at your option) any later version.                       *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful, but        *
# *   WITHOUT ANY WARRANTY; without even the implied warranty of            *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU      *
# *   Lesser General Public License for more details.                       *
# *                                                                         *
# *   You should have received a copy of the GNU Lesser General Public      *
# *   License along with FreeCAD. If not, see                               *
# *   <https://www.gnu.org/licenses/>.                                      *
# *                                                                         *
# ***************************************************************************

"""
This utility offers several commands to interact with the FreeCAD project on
crowdin. For it to work, you need a ~/.crowdin-freecad-token file in your
user's folder, that contains the API access token that gives access to the
crowdin FreeCAD project. The API token can also be specified in the
CROWDIN_TOKEN environment variable.

The CROWDIN_PROJECT_ID environment variable can be used to use this script
in other projects.

Usage:

    updatecrowdin.py <command> [<arguments>]

Available commands:

    gather:                       update all ts files found in the source code
                                  (runs updatets.py)
    status:                       prints a status of the translations
    update-source:                updates on CrowdIn the current version of .ts file
                                  found in the source code
    update-translation [locale]:  updates on CrowdIn the current version of locale .ts files
                                  passed to the command
    build:                        builds a new downloadable package on CrowdIn with all
                                  translated strings
    build-status:                 shows the status of the current builds available on
                                  CrowdIn
    download [build_id]:          downloads build specified by 'build_id' or latest if
                                  build_id is left blank
    apply / install:              applies downloaded translations to source code
                                  (runs updatefromcrowdin.py)

Example:

    ./updatecrowdin.py update

Setting the project name adhoc:

    CROWDIN_PROJECT_ID=some_project ./updatecrowdin.py update
"""

# NOTE: See CrowdIn API docs at: https://support.crowdin.com/developer/api/v2/

import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import namedtuple
from functools import lru_cache
from urllib.parse import quote_plus
from urllib.request import Request, urlopen, urlretrieve

TsFile = namedtuple("TsFile", ["filename", "src_path"])
translation_source = [TsFile("Quetzal.ts", "Quetzal.ts")]

# NOTE: location tuple contains:
# - module name
# - relative path to translation folder
WBLocation = namedtuple("WBLocation", ["module_name", "translations_path"])
wb_location = WBLocation("Quetzal", ".")

supported_locales = {
    "af": "af-ZA",
    "ar": "ar-SA",
    "eu": "eu-ES",
    "be": "be-BY",
    "bg": "bg-BG",
    "ca": "ca-ES",
    "zh-CN": "zh-CN",
    "zh-TW": "zh-TW",
    "hr": "hr-HR",
    "cs": "cs-CZ",
    "da": "da-DK",
    "nl": "nl-NL",
    "fil": "fil-PH",
    "fi": "fi-FI",
    "fr": "fr-FR",
    "gl": "gl-ES",
    "ka": "ka-GE",
    "de": "de-DE",
    "el": "el-GR",
    "hu": "hu-HU",
    "id": "id-ID",
    "it": "it-IT",
    "ja": "ja-JP",
    "kab": "kab-KAB",
    "ko": "ko-KR",
    "lt": "lt-LT",
    "no": "no-NO",
    "pl": "pl-PL",
    "pt-PT": "pt-PT",
    "pt-BR": "pt-BR",
    "ro": "ro-RO",
    "ru": "ru-RU",
    "sr": "sr-SP",
    "sr-CS": "sr-CS",
    "sk": "sk-SK",
    "sl": "sl-SI",
    "es-ES": "es-ES",
    "es-AR": "es-AR",
    "sv-SE": "sv-SE",
    "tr": "tr-TR",
    "uk": "uk-UA",
    "val-ES": "val-ES",
    "vi": "vi-VN",
}

GREEN = "\033[;32m" if os.name == "posix" else ""
NC = "\033[0m" if os.name == "posix" else ""  # no color

THRESHOLD = 20  # percent for all WB on CrowdIn, useless for each WB
DEBUG_URL = True


class CrowdinUpdater:
    BASE_URL = "https://api.crowdin.com/api/v2"

    def __init__(self, token, project_identifier, multithread=True):
        self.token = token
        self.project_identifier = project_identifier
        self.multithread = multithread

    @lru_cache()
    def _get_project_id(self) -> int:
        url = f"{self.BASE_URL}/projects/"
        response = self._make_api_req(url)

        for project in [p["data"] for p in response]:
            if project["identifier"] == project_identifier:
                return project["id"]

        raise Exception("No project identifier found!")

    def _make_api_req(self, url: str, extra_headers: dict = {}, method: str = "GET", data=None):
        headers = {"Authorization": "Bearer " + load_token(), **extra_headers}

        if type(data) is dict:
            headers["Content-Type"] = "application/json"
            data = json.dumps(data).encode("utf-8")

        request = Request(url, headers=headers, method=method, data=data)
        return json.loads(urlopen(request).read())["data"]

    def _make_project_api_req(self, project_path: str, *args, **kwargs):
        url = f"{self.BASE_URL}/projects/{self._get_project_id()}{project_path}"
        if DEBUG_URL:
            print(url)
        return self._make_api_req(url=url, *args, **kwargs)

    def _get_source_files_info(self) -> dict:
        files = self._make_project_api_req("/files?limit=250")
        return {f["data"]["path"].strip("/"): str(f["data"]["id"]) for f in files}

    def _add_storage(self, filename: str, fp):
        response = self._make_api_req(
            f"{self.BASE_URL}/storages",
            data=fp,
            method="POST",
            extra_headers={
                "Crowdin-API-FileName": filename,
                "Content-Type": "application/octet-stream",
            },
        )
        return response["id"]

    def _update_source_file(self, ts_file: TsFile, files_info: dict):
        filename = quote_plus(ts_file.filename)

        with open(ts_file.src_path, "rb") as fp:
            storage_id = self._add_storage(filename, fp)

        # only uploads the file if already exists
        if filename in files_info:
            file_id = files_info[filename]
            self._make_project_api_req(
                f"/files/{file_id}",
                method="PUT",
                data={
                    "storageId": storage_id,
                    "updateOption": "keep_translations_and_approvals",
                },
            )
            print(f"{filename} updated")
        else:
            self._make_project_api_req("/files", data={"storageId": storage_id, "name": filename})
            print(f"{filename} was not updated because is not on the list")

    def _upload_translation_file(self, ts_file: TsFile, files_info: dict):
        translation_filename = quote_plus(ts_file.filename)

        with open(ts_file.src_path, "rb") as fp:
            storage_id = self._add_storage(translation_filename, fp)

        locale = translation_filename.split("_")[1].split(".")[0]  # Extracts 'es-ES'

        src_filename = translation_source[0].filename

        if src_filename in files_info:
            file_id = files_info[src_filename]
            r = self._make_project_api_req(
                f"/translations/{supported_locales[locale]}",
                method="POST",
                data={
                    "storageId": storage_id,
                    "fileId": file_id,
                    "importEqSuggestions": "true",
                    "autoApproveImported": "false",
                    "translateHidden": "false",
                    "addToTm": "false",
                },
            )
            print_response(r)
        else:
            print(f"{translation_filename} was not updated because is not on the list")

    def status(self):
        response = self._make_project_api_req("/languages/progress?limit=100")
        return [item["data"] for item in response]

    def download(self, build_id: str):
        filename = f"{self.project_identifier}.zip"
        response = self._make_project_api_req(f"/translations/builds/{build_id}/download")
        urlretrieve(response["url"], filename)
        print("download of " + filename + " complete")

    def build(self):
        self._make_project_api_req("/translations/builds", data={}, method="POST")

    def build_status(self):
        response = self._make_project_api_req("/translations/builds")
        return [item["data"] for item in response]

    def update_source(self, ts_files: list):
        files_info = self._get_source_files_info()
        futures = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for ts_file in ts_files:
                if self.multithread:
                    future = executor.submit(self._update_source_file, ts_file, files_info)
                    futures.append(future)
                else:
                    self._update_source_file(ts_file, files_info)

        # This blocks until all futures are complete and will also throw any exception
        for future in futures:
            future.result()

    def update_translation(self, ts_files: list):
        files_info = self._get_source_files_info()
        print(files_info)
        futures = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for ts_file in ts_files:
                if self.multithread:
                    future = executor.submit(self._upload_translation_file, ts_file, files_info)
                    futures.append(future)
                else:
                    self._upload_translation_file(ts_file, files_info)

        # This blocks until all futures are complete and will also throw any exception
        for future in futures:
            future.result()


def print_response(response: dict):
    print(json.dumps(response, indent=2))


def load_token() -> None | str:
    """Loads API token stored in ~/.crowdin-freecad-token"""
    config_file = os.path.expanduser("~") + os.sep + ".crowdin-freecad-token"
    if not os.path.exists(config_file):
        config_file = os.path.expanduser("~") + os.sep + ".crowdin-freecadaddons"
    if os.path.exists(config_file):
        with open(config_file) as file:
            return file.read().strip()
    return None


def applyTranslations():
    """Extracts files from ZIP file and copy TS files"""
    global tempfolder
    currentfolder = os.getcwd()
    tempfolder = tempfile.mkdtemp()
    print(f"Creating temp folder {tempfolder}")
    src = os.path.join(currentfolder, "freecad-addons.zip")
    dst = os.path.join(tempfolder, "freecad-addons.zip")
    if not os.path.exists(src):
        print(
            "freecad-addons.zip file not found! Aborting.\nRun 'download' command before this one."
        )
        sys.exit()
    shutil.copyfile(src, dst)
    os.chdir(tempfolder)
    zfile = zipfile.ZipFile("freecad-addons.zip")
    print("Extracting freecad-addons.zip...")
    zfile.extractall()
    os.chdir(currentfolder)
    if not os.path.exists(os.path.join(tempfolder, wb_location.module_name)):
        print(f"ERROR: Workbench path for {wb_location.module_name} not found!")
    else:
        print(f"Updating files for {GREEN}{wb_location.module_name}{NC}...")
        # Iterate over all locales
        for short_locale, full_locale in supported_locales.items():
            # Copy the translation files to the project directory
            oldname = wb_location.module_name + "_" + full_locale + ".ts"
            newname = wb_location.module_name + "_" + short_locale + ".ts"
            old_file = os.path.join(tempfolder, wb_location.module_name, oldname)
            new_file = os.path.join(wb_location.translations_path, newname)
            shutil.copyfile(old_file, new_file)
        print("Update of translations files has been completed.")


if __name__ == "__main__":
    command = None

    args = sys.argv[1:]
    if args:
        command = args[0]

    token = os.environ.get("CROWDIN_TOKEN", load_token())
    if command and not token:
        print("Token not found")
        sys.exit()

    project_identifier = "freecad-addons"

    updater = CrowdinUpdater(token, project_identifier)

    if command == "status":
        status = updater.status()
        status = sorted(status, key=lambda item: item["translationProgress"], reverse=True)
        # NOTE: this check progress for all WB on CrowdIn, not only the current one
        print(
            len([item for item in status if item["translationProgress"] > THRESHOLD]),
            f"languages with status > {str(THRESHOLD)}%:\n",
        )
        sep = False
        for item in status:
            if item["translationProgress"] > 0:
                if (item["translationProgress"] < THRESHOLD) and (not sep):
                    print("\nOther languages:\n")
                    sep = True
                print(
                    f"{GREEN}{item['languageId']}{NC} {str(item['translationProgress'])}% "
                    f"({str(item['approvalProgress'])}% approved)"
                )

    elif command == "build-status":
        for item in updater.build_status():
            print(f"  id: {item['id']} progress: {item['progress']}% status: {item['status']}")

    elif command == "build":
        updater.build()

    elif command == "download":
        if len(args) == 2:
            updater.download(args[1])
        else:
            stat = updater.build_status()
            if not stat:
                print("no builds found")
            elif len(stat) == 1:
                updater.download(stat[0]["id"])
            else:
                print("available builds:")
                for item in stat:
                    print(
                        f"  id: {item['id']} progress: {item['progress']}% status: {item['status']}"
                    )
                print("please specify a build id")

    elif command in ["apply", "install"]:
        applyTranslations()
        subprocess.run(["./update_translation.sh", "-U"])  # update ts files
        subprocess.run(["./update_translation.sh", "-R"])  # release qm files
        subprocess.run(["./update_translation.sh", "-A"])  # git add and commit above threshold

    elif command == "gather":
        # Update agnostic file
        subprocess.run(["./update_translation.sh", "-u"])

    elif command == "update-source":
        # Execute after "gather"" command
        print("ts file being uploaded to CrowdIn: ", translation_source)
        updater.update_source(translation_source)

    elif command == "update-translation":
        print("Still does not work")
        exit(69)
        locale_source = []
        for arg in args[1:]:
            locale_source.append(TsFile(f"Quetzal_{arg}.ts", f"Quetzal_{arg}.ts"))
            updater.update_translation(locale_source)

        print(locale_source)

    else:
        print(__doc__)
