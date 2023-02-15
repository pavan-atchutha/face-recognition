from django.shortcuts import render, HttpResponse, redirect
from .models import *
from .forms import *
import face_recognition
import cv2
import numpy as np
import winsound
from django.db.models import Q
from playsound import playsound
import os
import pickle
from csv import writer
from csv import reader
from django.shortcuts import render
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.urls import reverse
import pandas as pd
from datetime import datetime
from django.core.files.storage import FileSystemStorage


last_face = 'no_face'
current_path = os.path.dirname(__file__)
sound_folder = os.path.join(current_path, 'sound/')
face_list_file = os.path.join(current_path, 'face_list.txt')
sound = os.path.join(sound_folder, 'beep.wav')
nameList=[]
flag=0


def index(request):
    scanned = LastFace.objects.all().order_by('date').reverse()
    present = Profile.objects.filter(present=True).order_by('updated').reverse()
    absent = Profile.objects.filter(present=False).order_by('shift')
    context = {
        'scanned': scanned,
        'present': present,
        'absent': absent,
    }
    return render(request, 'core/index.html', context)


def ajax(request):
    last_face = LastFace.objects.last()
    context = {
        'last_face': last_face
    }
    return render(request, 'core/ajax.html', context)


def scan(request):

    global last_face
    global flag
    flag=0
    known_face_encodings = []
    known_face_names = []

    profiles = Profile.objects.all()
    data = {}
    data = pickle.loads(open('pickle_file.pickle',"rb").read())
    print(data)
    for profile in profiles:
        person = str(profile.phone)
        person_name=profile.first_name
        # image_of_person = face_recognition.load_image_file(f'media/{person}')
        # person_face_encoding = face_recognition.face_encodings(image_of_person)[0]
        known_face_encodings.append(data[person])
        known_face_names.append(person_name)


    video_capture = cv2.VideoCapture(0)

    face_locations = []
    face_encodings = []
    face_names = []
    process_this_frame = True

    while True:
        if(flag==1):
            break
        ret, frame = video_capture.read()
        small_frame = cv2.resize(frame, (0, 0),None,fx=0.25, fy=0.25)
        # rgb_small_frame = small_frame[:, :, ::-1]
        rgb_small_frame=cv2.cvtColor(small_frame,cv2.COLOR_BGR2RGB)

        if process_this_frame:
            face_locations = face_recognition.face_locations(rgb_small_frame,number_of_times_to_upsample=2)
            face_encodings = face_recognition.face_encodings(rgb_small_frame,model='large',known_face_locations=face_locations )

            face_names = []
            for face_encoding in face_encodings:
                mat = False
                
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = "Unknown"

                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if(face_distances[best_match_index] <= 0.38):
                    mat = True
                if mat == True:
                    name =  known_face_names[best_match_index]
                elif mat ==False:
                
                    name = "Unknown!"
                if matches[best_match_index] and mat:
                    name = known_face_names[best_match_index]

                    profile = Profile.objects.get(Q(image__icontains=name))
                    if profile.present == True:
                        pass
                    else:
                        profile.present = True
                        winsound.PlaySound(sound, winsound.SND_ASYNC)
                        markAttendance(profile)
                        profile.save()

                    if last_face != name:
                        last_face = LastFace(last_face=name)
                        last_face.save()
                        last_face = name
                        # winsound.PlaySound(sound, winsound.SND_ASYNC)
                    else:
                        pass

                face_names.append(name)

        process_this_frame = not process_this_frame

        for (top, right, bottom, left), name in zip(face_locations, face_names):
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

            cv2.rectangle(frame, (left, bottom - 35),
                          (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6),
                        font, 0.5, (255, 255, 255), 1)

        cv2.imshow('Video', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()
    return HttpResponse('scaner closed', last_face)


def profiles(request):
    profiles = Profile.objects.all()
    context = {
        'profiles': profiles
    }
    return render(request, 'core/profiles.html', context)


def details(request):
    try:
        last_face = LastFace.objects.last()
        profile = Profile.objects.get(Q(image__icontains=last_face))
    except:
        last_face = None
        profile = None

    context = {
        'profile': profile,
        'last_face': last_face
    }
    return render(request, 'core/details.html', context)


def add_profile(request):
    form = ProfileForm
    if request.method == 'POST':
        form = ProfileForm(request.POST,request.FILES)
        if form.is_valid():
            #encoding_image(name,image)
            form.save()
            encoding_image(str(request.POST.get("phone")),request.FILES["image"])
            return redirect('profiles')
    context={'form':form}
    return render(request,'core/add_profile.html',context)


def edit_profile(request,id):
    profile = Profile.objects.get(pk=id)
    form = ProfileForm(instance=profile)
    if request.method == 'POST':
        form = ProfileForm(request.POST,request.FILES,instance=profile)
        if form.is_valid():
            print(404)
            #encoding_image(name,image)
            form.save()
            encoding_image(str(request.POST.get("phone")),request.FILES["image"])
            #encoding_image(request.POST.get("phone"),request.POST.get("image"))
            return redirect('profiles')
    context={'form':form}
    return render(request,'core/add_profile.html',context)


def delete_profile(request,id):
    profile = Profile.objects.get(pk=id)
    profile.delete()
    return redirect('profiles')


def clear_history(request):
    history = LastFace.objects.all()
    history.delete()
    return redirect('index')


def reset(request):
    profiles = Profile.objects.all()
    for profile in profiles:
        if profile.present == True:
            profile.present = False
            profile.save()
        else:
            pass
    history = LastFace.objects.all()
    history.delete()
    return redirect('index')



def markAttendance(profile):
    now = datetime.now()
    today = now.strftime("%Y/%m/%d_%H:%M")
    filename = "media/documents/" + datetime.now().strftime("%Y-%m-%d") + ".csv"
    # f = open(filename, "w", encoding="utf-8-sig", newline="")
    print(401)
    try:
        print(402)
        with open(filename, 'a') as f:
            print(403)
            print(profile.first_name)
            #for profile in nameList :
                # now = datetime.now()
                # dtString = now.strftime('%H:%M:%S')
                # f.writelines(f'\n{name},{dtString},{sid_name[sid.index(name)]}')
            f.writelines(f'\n{profile.first_name},{profile.last_name},{profile.date},{profile.hostelname},{profile.roomno}')
            f.close()
    except:
        print(404)
        with open(filename, 'w') as f:
            print(profile.first_name)
            #for profile in nameList :
                # now = datetime.now()
                # dtString = now.strftime('%H:%M:%S')
                # f.writelines(f'\n{name},{dtString},{sid_name[sid.index(name)]}')
            f.writelines(f'\n{profile.first_name},{profile.last_name},{profile.date},{profile.hostelname},{profile.roomno}')
            f.close()

 
def encoding_image(name,image):
    # Step 1: Open the pickle file in append mode
    print(404)
    try:
        print(os.path.getsize("pickle_file.pickle"))
        if os.path.getsize("pickle_file.pickle") > 0:
            print(1)
            pickle_file = open('pickle_file.pickle', 'rb')
            print(2)
            pickled_object = pickle.load(pickle_file)

        else:
            pickled_object={}
        image_of_person = face_recognition.load_image_file(image)
        person_face_encoding = face_recognition.face_encodings(image_of_person,num_jitters=100)[0]
        if name in pickled_object.keys():
            del pickled_object[name]
        pickled_object[name]=person_face_encoding
        pickle_file=open('pickle_file.pickle', 'wb')
        pickle.dump(pickled_object, pickle_file )
        pickle_file.close()
    except EOFError:
        # print(pickled_object = pickle.load(pickle_file))
        pickled_object = {}

def camoff(request):
    global flag
    flag=1
    return redirect('index')
    
    



