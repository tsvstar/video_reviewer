import subprocess
from multiprocessing import Pool
import os, sys, time

def run_command(filepath):
    command = ['C:\\MY\\opencv\\ffprobe.exe', '-show_entries', 'frame=pict_type', '-of', 'default=noprint_wrappers=1', filepath]
    cachedir = "%s/.cache"%os.path.dirname(filepath)
    if not os.path.exists(cachedir):
       os.mkdir(cachedir)

    tgtpath = "%s/%s.cache" % (cachedir,os.path.split(filepath)[1])
    if os.path.exists(tgtpath) and os.path.getsize(tgtpath):
       command1 = ['C:\\MY\\opencv\\ffprobe.exe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=nb_frames', '-of', 'default=noprint_wrappers=1', filepath]
       result = subprocess.run(command1, capture_output=True, text=True)

       num_frames = result.stdout.strip().split('=')[-1]
       cached_num_frames = os.path.getsize(tgtpath)  ##"nb_frames=%s" % os.path.getsize(tgtpath)
       try:
          num_frames_int = int(num_frames)
       except:
          num_frames_int = 0
       if abs(cached_num_frames - num_frames_int):
           ##print("%s - same size (%s)"%(filepath,num_frames))
           return filepath,""
       else:
           print("%s - diff size (%s/%s)" % (filepath,num_frames,cached_num_frames))
    print( "+ %s" % filepath)

    start = time.time()
    result = subprocess.run(command, capture_output=True, text=True)
    output = result.stdout.strip()
    end = time.time()

    print("%s - %s [%d sec] %s" % (tgtpath, len(output.split("\n")), (end-start), result.__dict__.keys()))
    with open(tgtpath, "wb") as fp:
        fp.write( output.replace('pict_type=','').replace("\n","").encode('utf-8') )
    return filepath, output

def run_commands_parallel(filenames, num_processes):
    # Create a multiprocessing pool with the specified number of processes
    pool = Pool(num_processes)

    # Map the filenames to the run_command function using the multiprocessing pool
    results = pool.map(run_command, filenames)

    # Close the multiprocessing pool
    pool.close()
    pool.join()

    # Create a dictionary from the results
    #output_dict = dict(results)
    #return output_dict

def collect_cache(path):
    global files_to_process
    if path=='-R':
        return
    print("do_caching %s" % repr(path))
    filenames = os.listdir(path)  # Replace with your list of filenames
    filenames = filter(lambda s: s.endswith('.mp4') or s.endswith('.mkv'), filenames)
    filenames = list(map( lambda s: "%s/%s" % (path,s), filenames))
    #for f in filenames:  run_command(f)
    #return
    files_to_process.extend(filenames)

def do_caching(filenames):
    if not filenames:
       print ("Nothing to do")
       return
    num_processes = 4  # Number of processes to run in parallel
    output_dict = run_commands_parallel(filenames, num_processes)
    #print(output_dict)

def recursive_collect_cache(path):
    if path=='-R':
        return

    print("recursive %s" % path)
    path = path.rstrip('/').rstrip('\\')
    collect_cache(path)
    try:
         for p in os.listdir(path):
              if p in ('.','..'):
                   continue
              if p.endswith('[done]'):
                   continue
              p = "%s/%s" % (path,p)
              if os.path.isdir(p):
                  print(p)
                  recursive_collect_cache(p)
    except Exception as e:
         print("%s: %s" % (type(e),e))

if __name__=="__main__":
    #do_caching(sys.argv[1])
    files_to_process = []
    for p in sys.argv[1:]:
       if '-R' in sys.argv:
          recursive_collect_cache(p)
       else:
          collect_cache(p)
    do_caching(files_to_process)
