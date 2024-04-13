import os, sys

def get_cut_name( filename ):
    cut_name = ( filename
                   .split('.mp4')[0].split('.mkv')[0]
                   .split('-mtslv5')[0].split('_lmc_8')[0].split('_mtsl5')[0]
                   .split('-4khevc')[0].split('_4khevc')[0]
                   .split('-hevc')[0].split('_hevc')[0]
                   .split('-crf')[0].split('_crf')[0] )
    return cut_name


to_compare = "." if len(sys.argv)<=1 else sys.argv[1]
to_compare = to_compare.replace("\\","/").rstrip("/")
if not os.path.isdir(to_compare):
   raise Exception("Not a dir")
if (to_compare=="."):
    to_compare = os.getcwd().replace("\\","/")
base_dirname = to_compare

videos = {}
prefixes = []
if True:
    for f in sorted(os.listdir(base_dirname)):
        f1 = f.split('.TRY_')[0]
        if (f1.endswith('.mp4') or f1.endswith('.mkv')):
          fullname = "%s/%s"%(base_dirname,f)
          ##print("%s: %s" % (f1,os.path.getsize(fullname)))
          cut_name = get_cut_name(f1)
          videos.setdefault(cut_name, [])
          videos[cut_name].append(fullname)
    for k in sorted(videos.keys()):
        if len(videos[k]) >= 2:
           prefixes.append(k)
    if not len(prefixes):
        print( "No packs found at %s" % base_dirname)
        exit(1)

    for prefix in prefixes:
         sizes = []
         print( "%s: %s" % (prefix, videos[prefix]))
         for fname in videos[prefix]:
            sizes.append( os.path.getsize(fname) )
         for i in range(1,len(sizes)):
            if sizes[0]*0.75 < sizes[i]:
              os.rename( videos[prefix][i], videos[prefix][i] + "_TOO_BIG" )
            elif sizes[i]<1024:
              os.rename( videos[prefix][i], videos[prefix][i] + "_TOO_SMALL" )
               

         #print ('|'.join(videos[prefix]))
