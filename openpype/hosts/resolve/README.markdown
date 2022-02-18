#### Basic setup

-   Install [latest DaVinci Resolve](https://sw.blackmagicdesign.com/DaVinciResolve/v16.2.8/DaVinci_Resolve_Studio_16.2.8_Windows.zip?Key-Pair-Id=APKAJTKA3ZJMJRQITVEA&Signature=EcFuwQFKHZIBu2zDj5LTCQaQDXcKOjhZY7Fs07WGw24xdDqfwuALOyKu+EVzDX2Tik0cWDunYyV0r7hzp+mHmczp9XP4YaQXHdyhD/2BGWDgiMsiTQbNkBgbfy5MsAMFY8FHCl724Rxm8ke1foWeUVyt/Cdkil+ay+9sL72yFhaSV16sncko1jCIlCZeMkHhbzqPwyRuqLGmxmp8ey9KgBhI3wGFFPN201VMaV+RHrpX+KAfaR6p6dwo3FrPbRHK9TvMI1RA/1lJ3fVtrkDW69LImIKAWmIxgcStUxR9/taqLOD66FNiflHd1tufHv3FBa9iYQsjb3VLMPx7OCwLyg==&Expires=1608308139)
-   add absolute path to ffmpeg into openpype settings
    ![image](https://user-images.githubusercontent.com/40640033/102630786-43294f00-414d-11eb-98de-f0ae51f62077.png)
-   install Python 3.6 into `%LOCALAPPDATA%/Programs/Python/Python36` (only respected path by Resolve)
-   install OpenTimelineIO for 3.6 `%LOCALAPPDATA%\Programs\Python\Python36\python.exe -m pip install git+https://github.com/PixarAnimationStudios/OpenTimelineIO.git@5aa24fbe89d615448876948fe4b4900455c9a3e8` and move built files from `%LOCALAPPDATA%/Programs/Python/Python36/Lib/site-packages/opentimelineio/cxx-libs/bin and lib` to `%LOCALAPPDATA%/Programs/Python/Python36/Lib/site-packages/opentimelineio/`. I was building it on Win10 machine with Visual Studio Community 2019 and
    ![image](https://user-images.githubusercontent.com/40640033/102792588-ffcb1c80-43a8-11eb-9c6b-bf2114ed578e.png) with installed CMake in PATH.
-   install PySide2 for 3.6 `%LOCALAPPDATA%\Programs\Python\Python36\python.exe -m pip install PySide2`
-   make sure Resolve Fusion (Fusion Tab/menu/Fusion/Fusion Settings) is set to Python 3.6
    ![image](https://user-images.githubusercontent.com/40640033/102631545-280b0f00-414e-11eb-89fc-98ac268d209d.png)

#### Editorial setup

This is how it looks on my testing project timeline
![image](https://user-images.githubusercontent.com/40640033/102637638-96ec6600-4156-11eb-9656-6e8e3ce4baf8.png)
Notice I had renamed tracks to `main` (holding metadata markers) and `review` used for generating review data with ffmpeg confersion to jpg sequence.

1.  you need to start OpenPype menu from Resolve/EditTab/Menu/Workspace/Scripts/**__OpenPype_Menu__**
2.  then select any clips in `main` track and change their color to `Chocolate`
3.  in OpenPype Menu select `Create`
4.  in Creator select `Create Publishable Clip [New]` (temporary name)
5.  set `Rename clips` to True, Master Track to `main` and Use review track to `review` as in picture
    ![image](https://user-images.githubusercontent.com/40640033/102643773-0d419600-4160-11eb-919e-9c2be0aecab8.png)
6.  after you hit `ok` all clips are colored to `ping` and marked with openpype metadata tag
7.  git `Publish` on openpype menu and see that all had been collected correctly. That is the last step for now as rest is Work in progress. Next steps will follow.
