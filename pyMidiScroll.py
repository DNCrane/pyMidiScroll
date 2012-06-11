"""
TODO: cleanup
TODO: pick colors more intelligently
TODO: include run-in file so video doesn't start immediately playing
technique: make two avis, one for the run-up and one that starts immediately. Then combine them.
mencoder -ovc lavc start.avi end.avi -o complete.avi

DONE:
*make it so that shorter notes appear on top of bigger ones so they're not hidden
technique: make a list of notes, sort them by duration, and then draw them all at once.
*autodetect mp3 length + higher precision
*autodetect highest/lowest note and set offsets appropriately

"""
import pygame
import random
import midi
import Queue
import os

def getMP3Duration(mp3_file):
    mp3_file=mp3_file.replace(" ","\\ ")
    x=os.popen("ffmpeg -i " + mp3_file + " 2>&1 | grep Duration")
    time=x.readline()
    print time
    time=time.split(" ")[3].split(":")
    time=float(time[0])*60*60+float(time[1])*60+float(time[2][:-1])
    return time

"""
Returns a list of lists of notes and the number of ticks. Each note is of the form
[pitch,velocity,start_time,end_time]
where start_time and end_time are in ticks (which has no relation to
time or picture frames)

Each track from the midi is represented as a different list of notes.
"""
def get_note_lists(tracks):
    note_lists = []
    max_len = 0
    max_len2 = 0
    lowest_note=9999
    highest_note=0
    for track in tracks:
        note_dic = {}
        note_list = []
        for event in track.events:    
            if(event.time>max_len2):
                max_len2=event.time    
            if event.type == 'NOTE_ON' or event.type == 'NOTE_OFF':
                if(not event.pitch in note_dic):
                    note_dic[event.pitch]=[event.velocity, event.time]
                else:
                    note_list+=[[event.pitch]+note_dic.pop(event.pitch)+[event.time]]
                if(event.time>max_len):
                    max_len=event.time
                if(event.pitch<lowest_note):
                    lowest_note=event.pitch
                if(event.pitch>highest_note):
                    highest_note=event.pitch
            if event.type == "END_OF_TRACK":
                print event
        note_lists+=[note_list]
    note_lists+=[[[-100,0,0,100]]]
    print "max_len:", max_len, max_len2
    return (max_len, note_lists, lowest_note, highest_note)

def make_pictures(midi_file, mp3_file):
    mainloop, fps, screen_width, screen_height =  True, 30., 400, 320
    offset=-screen_width
    song_duration = getMP3Duration(mp3_file)
    print song_duration
    pygame.init()

    screen = pygame.display.set_mode([screen_width,screen_height])
    screen.fill([0,0,0])

    Clock = pygame.time.Clock()
    m = midi.MidiFile()
    m.open(midi_file)
    m.read()

    (max_len, note_lists, lowest_note, highest_note) = get_note_lists(m.tracks)
    note_range = highest_note-lowest_note
    pitch_height = float(screen_height-30)/note_range  #the number of pixels difference for going up by 1 in pitch
    height_offset = screen_height + lowest_note*pitch_height - 15
    #print height_offset-highest_note*pitch_height

    colors=[]
    for i in xrange(len(note_lists)):
        colors+=[[random.randint(0,255), random.randint(0,255), random.randint(0,255)]]
        colors[-1][random.randint(0,2)]=15

    ticksPerPixel=float(max_len)/(fps*song_duration)
    print ticksPerPixel, "tpp"
    pygame.mixer.music.load(mp3_file)
    playing=False

    os.system("mkdir " + midi_file + "tmp1")
    os.system("mkdir " + midi_file + "tmp2")
    folder = midi_file + "tmp1"
    while mainloop:
        Clock.tick(fps)
        pygame.display.set_caption("Press Esc to quit. FPS: %.2f" % (Clock.get_fps()))
        screen.fill((0,0,0))

        i=0
        rects=Queue.PriorityQueue()
        for notes in note_lists:
            #Put all of the rectangles we are going to draw into a priority queue
            #sorted by duration, so that shorter notes don't get covered
            #by longer ones when we draw them on the screen.
            for note in notes:
                rect = (note[2]/ticksPerPixel-offset,
                        height_offset-note[0]*pitch_height,
                        (note[3]-note[2])/ticksPerPixel-1,
                        2+note[1]/32)
                if(note[3]==max_len and rect[0]+rect[2]<screen_width/2):
                    mainloop=False
                if(rect[0]>screen_width or rect[0]+rect[2]<0):
                    continue
                #print "note: ", rect
                if(rect[0]<=screen_width/2):
                    folder = midi_file + "tmp2"
                if(rect[0]<=screen_width/2 and rect[0]+rect[2]>=screen_width/2):
                    if(not playing):
                        #pygame.mixer.music.play(0,0)
                        playing=True
                    color=(255,255,255)
                else:
                    color = colors[i]
                #use duration as key
                rects.put((-rect[2],color,rect))
            i+=1
        while not rects.empty():
            rect=rects.get()
            #print rect[0], rects.qsize()
            pygame.draw.rect(screen,rect[1],rect[2])
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                mainloop = False # Be IDLE friendly!
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    mainloop = False # Be IDLE friendly!
        pygame.display.update()
        index=str(offset+screen_width)
        index='0'*(10-len(index))+index
        pygame.image.save(screen,folder + "/frame" + index + ".png")
        offset+=1
    print offset
    pygame.quit() # Be IDLE friendly! 

def makeMP3Fluid(midi_file,soundfont_file="~/soundfonts/SGM-V2.01.sf2"):
    os.system("fluidsynth -l -F fluid"+midi_file+".wav " + soundfont_file + " " + midi_file)
    return "fluid"+midi_file+".wav"

def makeMP3Timidity(midi_file):
    os.system("timidity " + midi_file + " -Ow -o " + midi_file + ".wav")
    return midi_file+".wav"

def make_video(midi_file):
    mp3_file = makeMP3Fluid(midi_file)
    make_pictures(midi_file,mp3_file)
    mp3_file = makeMP3Timidity(midi_file)
    #make video of midi
    os.system("mencoder mf://"+midi_file+"tmp2/*.png \
-mf w=400:h=320:fps=30:type=png -ovc lavc -lavcopts \
vcodec=mpeg4:mbd=2:trell -oac copy -o tmp"+midi_file+".avi")
    #add sound to midi video
    os.system("mencoder -ovc copy -audiofile "+mp3_file+"\
 -oac copy tmp"+midi_file+".avi -o "+midi_file+".avi")

    #make the video for the "run-in" (no music playing)
    #os.system("mencoder mf://"+midi_file+"tmp1/*.png \
#-mf w=400:h=320:fps=30:type=png -ovc lavc -lavcopts \
#vcodec=mpeg4:mbd=2:trell -oac copy -o tmpRunin"+midi_file+".avi")
    #add sound to run-in video
#    os.system("mencoder -ovc copy -audiofile silence.wav\
# -oac copy tmpRunin"+midi_file+".avi -o tmpRunin"+midi_file+".avi")

    #combine run-in and song
    #os.system("mencoder -oac copy -ovc copy tmpRunin"+midi_file+".avi "+midi_file+".avi -o FULL"+midi_file+".avi")
    return 1

#make_video("Dream_Land.mid")

