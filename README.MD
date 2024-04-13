## compare_video.py

  Visual comparison of given list videos or all groups of videos in current directory.
  Its primary purpose is check visual quality of filtering/re-compression result.
  It is assumed that videos in the compared group have same aspect ratio and it is nice to have same frame number.
  For case of current directory scan - videos are grouped by their "body" which is defined by `get_cut_name()`.  
**Requires** opencv 4.7.0 and python 3.10

## cleanup_video.py

Aux tool to quickly exclude too large and obviously broken result videos

## make_cache_picttype.py

  Aux tool to create maps of frame types for each video in the current directory.
  That is a helper for the "compare_video.py", which uses result cache to display that frame info.
**Requires** ffprobe.exe from ffmpeg package
