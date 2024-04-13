# TODO correct moving for pack with different zooming
# TODO do offset
# TODO do not fail on minimize

import cv2
import sys, os, json, subprocess
from datetime import datetime
import numpy as np

CONF_ALLOW_SINGLE = False       # If True - too not only compare but be able to see "stopframe" all videos
CONF_KEEP_IN_MEMORY = False	# If True - do not unload on switch for faster processing (but eat memory) [TODO]


def log(s, *kw):
    s = str(s)
    if len(kw)>0:
       s += "\t"
       s +="\t".join(map(str,kw))
    with open(__file__+".log","at",encoding="utf-8",errors="replace") as fp:
       fp.write(s+"\n")
    print(s)

def get_video_prop(filepath, video):
    frame_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = video.get(cv2.CAP_PROP_FPS)
    num_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    dname,fname = os.path.split(filepath)
    cached_path = "%s/.cache/%s.cache" % (dname,fname)
    frame_types = ''
    if os.path.exists(cached_path):
       with open(cached_path,'rb') as fp:
           frame_types = fp.read().decode('utf-8')
    frame_types = frame_types + '?'*num_frames

    codec_code = int(video.get(cv2.CAP_PROP_FOURCC))
    fourcc = chr(codec_code & 0xFF) + chr((codec_code >> 8) & 0xFF) + chr((codec_code >> 16) & 0xFF) + chr((codec_code >> 24) & 0xFF)

    return (frame_width, frame_height, fps, num_frames,frame_types[:num_frames], fourcc)

def get_cut_name( filename ):
    cut_name = ( filename.split('.mp4')[0].split('.mkv')[0]
                   .split('-mtslv5')[0].split('_lmc_8')[0].split('_mtsl5')[0]
                   .split('.BLUR')[0]
                   .split('-4khevc')[0].split('_4khevc')[0]
                   .split('-hevc')[0].split('_hevc')[0]
                   .split('-crf')[0].split('_crf')[0] )
    return cut_name

def find_pack(video_path):
    global videos, enforce_key
    dirname, filename = os.path.split(video_path)
    cut_name = get_cut_name(filename)
    if enforce_key:
       cut_name = enforce_key
    log("Lookup pack for:%s\n" % cut_name)
    log( "1: %s" % os.path.split(video_path)[1] )
    return list(videos[cut_name]) #map(lambda f: "%s/%s"%(dirname,f),videos[cut_name]) )

def get_prefix_idx(video_path):
    global prefixes
    dirname, filename = os.path.split(video_path)
    cut_name = get_cut_name(filename)
    idx = 0
    log("get_prefix_idx() prefixes = %s" % cut_name)
    for p in prefixes:
        if p >= cut_name:
            log("%s <= %s" %  (cut_name,p))
            return idx
        log("%s > %s" % (cut_name,p))
        idx = idx + 1
    log("Prefix IDX=%s" % idx)
    return idx   

def WAS1():
    rv = [video_path]
    for f in sorted(os.listdir(dirname)):
        if ( f!=filename and f.startswith(cut_name) 
		and (f.endswith('.mp4') or f.endswith('.mkv'))):
           path = "%s/%s" % (dirname,f)
           rv.append(path)
    return rv

def putText(frame, y,txt):
       global color
       cv2.putText(
                frame,
                txt,
                (10, y), # pos
                cv2.FONT_HERSHEY_COMPLEX,
                0.5,      #zoom
                color,
                1,        # thickness
                cv2.LINE_AA,
            )

def compare(video_path):
    global color, prefixes
    global firstTime
    global frame_index

    prefix_idx = get_prefix_idx(video_path) 

    frame_index = 0
    frame_index_was = None
    dragging = False		# drag&drop sequence
    drag_start =(0,0)
    zoom_factor = 1		# zoom (applied for primary video)
    zoom_video  = 1             # extra zoom to be exactly same appearance as primary video
    top_left = [0,0]		# top-left corner (applied to primary video)
    was_output=""		# to print debug output only if changed
    selected_video_index = 0	# which one video is displayed
    message = []                # output on the screen


    video1 = cv2.VideoCapture(video_path)
    frame_width1, frame_height1, fps1, num_frames1, frame_types1, fourcc1 = get_video_prop(video_path,video1)
    aspect1 = frame_width1 / frame_height1

    compare_list = [ [video_path, frame_width1, frame_height1, fps1, num_frames1, frame_types1, None, 0, fourcc1] ]
   
    video_path = video_path.replace("\\","/")
    ##compare_video_list = [video1]
    for path in find_pack(video_path):
        log(path, video_path)
        if (path==video_path):
           continue

        f = os.path.split(path)[1]
        v = cv2.VideoCapture(path)
        w,h, fps, sz, frame_types, fourcc = get_video_prop(path, v)
        if w==0 or h==0:
           log( "... %s - ignore because zero (w=%s,h=%s)" % (f,w,h))
        elif (aspect1 == h/w) or (1/aspect1 == w/h):
           #print( "... %s - SEEMS ROTATED - aspect (%s) inverted to primary(%s)" % (f,w/h,aspect1))
           log( "%d: %s [ROTATED]" % (len(compare_list)+1, f) )
           compare_list.append([path, h, w, fps, sz, frame_types, cv2.ROTATE_90_CLOCKWISE, 0,fourcc])

        elif aspect1 != w/h:
           log( "... %s - ignore because aspect (%s) differ from primary(%s)" % (f,w/h,aspect1))
        elif num_frames1 != sz and enforce_key is None:
           log( "... %s - ignore because num of frames (%s) differ from primary(%s)" % (f,sz,num_frames1))
        else:
           log( "%d: %s" % (len(compare_list)+1, f) )
           compare_list.append([path, w, h, fps, sz, frame_types, None, 0,fourcc])
           ##compare_video_list.append(v)
    v = None
    log('')

    path, frame_width, frame_height, fps, num_frames, frame_types, rotated, frame_offset,fourcc = compare_list[0]
       
    #def on_trackbar_move(value):
    #    nonlocal frame_index
    #    frame_index = value

    def on_mouse(event, x, y, flags, param):
        nonlocal top_left, dragging, drag_start

        if event == cv2.EVENT_LBUTTONDOWN:
            drag_start = (x, y)
            dragging = True

        elif event == cv2.EVENT_LBUTTONUP:
            dragging = False

        elif event == cv2.EVENT_MOUSEMOVE and dragging:
            dx = x - drag_start[0]
            dy = y - drag_start[1]
            drag_start = (x, y)

            top_left = top_left[0]-dx, top_left[1]-dy
            #print("move", top_left[0], x, frame_width-window_zoomed_width)


    trackbar_name = "Progress"
    cv2.setTrackbarPos(trackbar_name, window_name, 0)
    cv2.setTrackbarMax(trackbar_name, window_name, num_frames-1)
    cv2.setMouseCallback(window_name, on_mouse)

    last_key = 0
    switched=False
    helpFlag = False
    askAction = None
    while True:

       cutname = prefixes[prefix_idx]
       if askAction=='Rename':
           suffix = input("Enter SUFFIX:").strip()
           askAction = None
           if len(suffix)!=0:
             video1 = None
             newpath = path + "." + suffix
             log("RENAMED TO:", newpath)
             os.rename(path, newpath)
             compare_list[selected_video_index][0] = newpath
             videos[cutname] = list(map(lambda p: newpath if p==path else p, videos[cutname]))
             path = newpath
             video1 = cv2.VideoCapture(path)

       k1 = cv2.waitKeyEx(100)
       if k1:
          last_key = k1
          if not helpFlag:
             message = []
       k = k1 #& 0xFF
       if k>0:
         log("Keypressed=%s" % k)
         if len(compare_list) <= 1:
            message = ['', "No action - that is single video"]
            log(message[-1])
            askAction = None

         if askAction=='Delete':
            message = []
            helpFlag = False
            if k==ord('Y') or k==ord('y'):
               video1 = None
               try:
                  os.rename(path, path+"_DEL")
                  log("DELETED:", path)
                  del compare_list[selected_video_index]
                  selected_video_index = -1
                  k = ord('1') if len(compare_list) > 1 else ord('+')
                  videos[cutname] = list(filter( lambda p: p!=path, videos[cutname]))
               except Exception as e:
                  print("%s: %s" % (type(e),e))
                  askAction = None
               print(compare_list)
               print(k)
         if askAction=='Keep':
            message = []
            helpFlag = False
            if k==ord('Y') or k==ord('y'):
               video1 = None
               try:
                  for i in range(len(compare_list),0,-1):
                     i = i-1
                     if i!=selected_video_index:
                        log("DELETE_MULTI:", compare_list[i][0])
                        os.rename(compare_list[i][0], compare_list[i][0]+"_DEL")
                        del compare_list[i]
                  k = ord('+')
               except Exception as e:
                  log("%s: %s" % (type(e),e))
                  askAction = None
               log(compare_list)
               log(k)

         # If after action one video in current pack is left
         if askAction in ['Keep','Delete']:
           if k==ord('+'):
             if prefix_idx+1 >= len(prefixes):
                 # Simple fallback if that is a last pack - just do not delete it
                 videos[cutname] = [path]
                 message = ['', 'That is a last pack']
                 k = ord('1')
             else:
                 # Normally - exclude the pack from the lists
                 del videos[cutname]
                 log("DELETE PACK #%s - %s" % (prefix_idx,prefixes[prefix_idx]))
                 del prefixes[prefix_idx]
                 log("KNOWN PREFIXES: %s" % (prefixes))
                 prefix_idx -= 1
           else:
             if selected_video_index >= len(compare_list):
                 selected_video_index = 0
           askAction = None


       if k==0x1b: 		#Escape
          break

       # QWER = switch zoom factor
       elif k==ord('q'):
           zoom_factor = 0.5
       elif k==ord('w'):
           zoom_factor = 1
       elif k==ord('e'):
           zoom_factor = 2
       elif k==ord('r'):
           zoom_factor = 4

       #1..9 = switch video inside of pack
       elif k>=ord('1') and k<=ord('9'):
          new_video_idx = k - ord('1')
          if new_video_idx < len(compare_list) and new_video_idx != selected_video_index:
              selected_video_index = new_video_idx
              path, frame_width, frame_height, fps, num_frames, frame_types, rotated, frame_offset, fourcc = compare_list[selected_video_index]
              frame_index_was = -1
              zoom_video = frame_width1/frame_width
              log("Switch to %s - zoom=%s" % (path,zoom_video))
              switched=True
              video1 = cv2.VideoCapture(path)

       elif k==ord('D'):
           message = [ "DELETE the file [y/N]?"]
           helpFlag=True
           askAction = 'Delete'
       elif k==ord('X'):
           message = [ "KEEP the only file [y/N]?"]
           helpFlag=True
           askAction = 'Keep'
       elif k==ord('R'):
           askAction = 'Rename'
           # Doesn't work because hang in input() before really goes to opencv
           #message = [ "Switch to console and input extra suffix..."]
           #helpFlag=True

       # P = switch text color
       elif k==ord('p'):
           if color==(255,0,0):   color=(0,255,0)
           elif color==(0,255,0): color=(0,0,255)
           elif color==(0,0,255): color=(0,0,0)
           elif color==(0,0,0):   color=(255,255,255)
           else:                  color=(255,0,0)

       elif k==ord('o') and selected_video_index==0:
           message = ['', "Can't rotate primary video"]
       elif k==ord('o') and selected_video_index!=0:
           if rotated is None:
              rotated = cv2.ROTATE_90_CLOCKWISE
           elif rotated == cv2.ROTATE_90_CLOCKWISE:
              rotated = cv2.ROTATE_180
           elif rotated == cv2.ROTATE_180:
              rotated = cv2.ROTATE_90_COUNTERCLOCKWISE
           else:
              rotated = None
           frame_width = compare_list[selected_video_index][2]
           frame_height = compare_list[selected_video_index][1]
           compare_list[selected_video_index][1] = frame_width 
           compare_list[selected_video_index][2] = frame_height
           compare_list[selected_video_index][6] = rotated  

       elif k==ord('-'):
          log("Previous pack (%s-1)" % prefix_idx )
          idx = prefix_idx - 1 
          if idx < 0:
             message = ['', 'That is a first pack']
          else:
             log("%s|%s\n%s"%(idx,prefixes[idx],videos[prefixes[idx]]))
             return videos[prefixes[idx]][0]
       elif k==ord('+') or k==ord('='):
          log("Next pack (%s+1)" % prefix_idx)
          idx = prefix_idx + 1 
          if idx >= len(prefixes):
             message = ['', 'That is a last pack']
             idx = prefix_idx
          else:
             return videos[prefixes[idx]][0]

       elif k==2424832:		#left
           top_left[0] = top_left[0] - 32
       elif k==2490368:		#up
           top_left[1] = top_left[1] - 32
       elif k==2555904:		#right
           top_left[0] = top_left[0] + 32
       elif k==2621440:		#down
           top_left[1] = top_left[1] + 32

       # PgUp/PgDn = prev/next frame
       elif k==2162688:		#pgup(left)
           frame_index = max(0, frame_index-1)
       elif k==2228224:		#pgdn(right)
           frame_index = min(num_frames-1, frame_index+1)

       elif k==ord('['):
           frame_offset = frame_offset-1
           compare_list[selected_video_index][7] = frame_offset
           frame_index_was = None
       elif k==ord(']'):
           frame_offset = frame_offset+1
           compare_list[selected_video_index][7] = frame_offset
           frame_index_was = None

       elif last_key==7340032:	# F1
           message = [ "F1 = this help", "1,2,3,4,.. = switch video", "q,w,e,r = zoom", "o = rotate current", "p = switch text color", "arrows = move window",
                       "pgup/pgdn = prev/next frame", "-/+ = prev/next pack", "Shift+D = mark this as Deleted", "Shift+X = mark all other videos of pack as deleted","Shift+R = rename"]
           helpFlag=True


       if frame_index != frame_index_was:
          real_frame_index = frame_index + frame_offset
          real_frame_index = max( 0, min( num_frames-1, real_frame_index ) )
          cv2.setTrackbarPos(trackbar_name, window_name, frame_index)
          video1.set(cv2.CAP_PROP_POS_FRAMES, real_frame_index)
          ret1, frame1 = video1.read()
          log("frame %s+%d/rv=%s"%(frame_index,frame_offset,ret1))
          if not ret1:
             log("fail %s"%ret1)
          frame_index_was = frame_index


       window_width = cv2.getWindowImageRect(window_name)[2]
       window_height = cv2.getWindowImageRect(window_name)[3]
       window_zoomed_width = int(window_width / zoom_factor)
       window_zoomed_height = int(window_height / zoom_factor)

       if window_width < 16 or window_height < 16:
            continue

       x,y = top_left[0], top_left[1]
       w,h = window_zoomed_width, window_zoomed_height

       x = max(0, min(x, frame_width1 - window_zoomed_width))
       y = max(0, min(y, frame_height1 - window_zoomed_height))
       output = "zm=%.1f  %-10s  %-4s %-4s  %-5s -> x1=[%-4s:%-4s] y1=[%-4s:%-4s]" % (zoom_factor, top_left, w, h, dragging, x+w, frame_width1, y+h, frame_height1)
       top_left = [x, y]

       # transform to current video params
       zoom_x, zoom_y, zoom_w, zoom_h = ( x/zoom_video, y/zoom_video, frame_width*zoom_video, frame_height*zoom_video)

       if rotated is not None:
          copy_frame = cv2.hconcat([frame1])
          copy_frame = cv2.rotate(copy_frame, rotated)
       else:
          copy_frame = cv2.hconcat([frame1])
       croped_frame = copy_frame[int(zoom_y):int(zoom_h), int(zoom_x):int(zoom_w)]
       resized_frame = cv2.resize(croped_frame, (int((frame_width1-x)*zoom_factor), int((frame_height1-y)*zoom_factor)))
       h1 = min(window_height,resized_frame.shape[0])
       w1 = min(window_width, resized_frame.shape[1])

       if switched or output!=was_output:
          switched=False
          log(output)
          log(zoom_x, ",", zoom_y, "/", x/zoom_video,",", y/zoom_video, "size:", zoom_w, zoom_h)
          log(">>", (resized_frame.shape[1],resized_frame.shape[0]), (window_width,window_height),(w1,h1) )
       was_output = output   

       # Create a black canvas with the window size
       canvas = np.zeros((window_height, window_width, 3), dtype=np.uint8)
       canvas[0:h1, 0:w1] = resized_frame[0:h1, 0:w1]
       result_frame = canvas

       fsize_megabytes = os.path.getsize(path)/(1024*1024)
       length_seconds = num_frames/fps
       total_rate_mbps =  (fsize_megabytes / length_seconds) * 8  # as that is megbIts per second - multiply 8
       try:
         putText( result_frame, 20, "[%d/%d] %s [%dMb / %.1fMbps / %dsec]" % (selected_video_index+1, len(compare_list), compare_list[selected_video_index][0], fsize_megabytes, total_rate_mbps, length_seconds ) )
         putText( result_frame, 40, "Progress %d/%d [%s x%s] %s:%dx%d@%d%s%s" % (frame_index,num_frames,frame_types[frame_index], zoom_factor, fourcc, frame_width,frame_height,fps," ROTATED" if rotated is not None else "",
                                  ("+%s" % frame_offset) if frame_offset else "") )
       except Exception as e:
         log("ERROR [%s] %s: %s" % (selected_video_index, type(e),e))
       #if k==ord('o') and selected_video_index==0:
       #    putText( result_frame, 80, "Can't rotate primary video")
       if len(message): #last_key==7340032:	# F1
           y = 60
           for t in message:
              putText( result_frame, y, t)
              y = y+20


       cv2.imshow(window_name, result_frame)

    video1.release()
    #cv2.destroyWindow(window_name)
    #cv2.destroyAllWindows()
    return None

now = datetime.now()
log("\n============================\nStart compare - %s" % now.strftime("%Y-%m-%d %H:%M:%S"))
to_compare = "." if len(sys.argv)<=1 else sys.argv[1]
videos = {}
prefixes = []
to_compare = to_compare.replace("\\","/").rstrip("/")
if (os.path.isdir(to_compare)):
   if (to_compare=="."):
       to_compare = os.getcwd().replace("\\","/")
   base_dirname = to_compare
elif to_compare.find("/")>0:
   base_dirname, _ = os.path.split(to_compare)
else:
   base_dirname = os.getcwd().replace("\\","/")
   to_compare = "%s/%s" % (base_dirname,to_compare)
   log("Implicitly use curdir: %s" % base_dirname)


enforce_key = None
if (not os.path.isdir(base_dirname)):
    log("Something goes wrong - %s is not a dir" % base_dirname)
    exit(1)
elif len(sys.argv)>2:
    log("Explicit compare list = ",sys.argv)
    videos = {}
    cut_name = get_cut_name(os.path.basename(to_compare))
    enforce_key = cut_name
    videos.setdefault(cut_name, [])
    prefixes.append(cut_name)
    for f in sys.argv[1:]:
      f = f.replace("\\","/").rstrip("/")
      if f.find("/")<0:
         f = "%s/%s" % (base_dirname,f)
      videos[cut_name].append(f)
      log(cut_name, f)
else:
    videos = {}
    log("Compare dir %s" % base_dirname)
    for f in sorted(os.listdir(base_dirname)):
        if (f.endswith('.mp4') or f.endswith('.mkv')):
          cut_name = get_cut_name(f)
          videos.setdefault(cut_name, [])
          path = "%s/%s" % (base_dirname,f)
          videos[cut_name].append(path)
    for k in sorted(videos.keys()):
        log("found%s" % len(prefixes), k, list(map(lambda f: f.split('/')[-1], videos[k])))
        if CONF_ALLOW_SINGLE or len(videos[k]) >= 2:
           prefixes.append(k)
    if not len(prefixes):
        log( "No packs found at %s" % base_dirname)
        exit(1)
    prefixes = list(sorted(prefixes))
    if base_dirname == to_compare:
        to_compare = videos[prefixes[0]][0]

if (os.path.exists(to_compare)):
   firstTime = True
   color = (255,0,0)		# color of text

   window_name = "Compare video" # static window name to remember size/position
   cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
   def on_trackbar_move(value):
        global frame_index
        frame_index = value
   cv2.createTrackbar("Progress", window_name, 0, 1, on_trackbar_move)

   #zipped_prefixes = list(map(lambda a: '%s=%s'%(a[0],repr(a[1])),zip(range(len(prefixes)),prefixes)))
   log("PREFIXES: [%s]" % ', '.join(prefixes))
   while (to_compare and os.path.exists(to_compare)):
       to_compare = compare(to_compare)  #"O:/mnt-shared/__Фотки2/baba lena/VID_20211031_114708.mp4")
       log("SWITCH TO: %s" % to_compare)
   if not to_compare:
       log("STOP")
   else:
       log("Not found to compare %s" % to_compare)
else:
   log("Not found - %s\nIf that is a .bat file and path includes cyrylic - ensure that 866 encoding is used"%to_compare)
