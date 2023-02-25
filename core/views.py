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
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate,login,logout
import pathlib
from django.http import FileResponse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext


last_face = 'no_face'
current_path = os.path.dirname(__file__)
sound_folder = os.path.join(current_path, 'sound/')
face_list_file = os.path.join(current_path, 'face_list.txt')
sound = os.path.join(sound_folder, 'beep.wav')
nameList=[]
flag=0

@login_required
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

@login_required
def ajax(request):
    last_face = LastFace.objects.last()
    context = {
        'last_face': last_face
    }
    return render(request, 'core/ajax.html', context)

@login_required
def scan(request):

    global last_face
    global flag
    flag=0
    known_face_encodings = []
    known_face_names = []
    date=datetime.now().strftime("%Y-%m-%d")
    profiles = Profile.objects.all()
    data = {}
    data = pickle.loads(open('pickle_file.pickle',"rb").read())
    pickel_attendance(str(date))
    attendance=pickle.loads(open('attendance.pickle',"rb").read())
    print(data)
    print(attendance)
    att=attendance[date]
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
    try:
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
                        if profile.present == True or profile.pk in att[1]:
                            messages.error(request,'Already present!')
                            pass
                        else:
                            print(profile.shift)
                            profile.present = True
                            winsound.PlaySound(sound, winsound.SND_ASYNC)
                            if len(att[0])==0:
                                print('all attendance over!')
                                messages.success(request, "All Attendance Over!!")
                                break
                            att[0].remove((profile.pk))
                            att[1].append(profile.pk)
                            print(attendance[date])
                            # markAttendance(profile)
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
                print("db sucessfully update!")
                messages.success(request, "attendance db Successfully updated!!")
                break
    except:
        messages.error(request,"Check person Credentials And Try again!")

    video_capture.release()
    cv2.destroyAllWindows()
    attendance[date]=att
    pickle_file=open('attendance.pickle', 'wb')
    pickle.dump(attendance, pickle_file )
    return HttpResponse('scaner closed', last_face)

@login_required
def profiles(request):
    profiles = Profile.objects.all()
    context = {
        'profiles': profiles
    }
    return render(request, 'core/profiles.html', context)

@login_required
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

@login_required
def add_profile(request):
    form = ProfileForm
    try:
        if request.method == 'POST':
            form = ProfileForm(request.POST,request.FILES)
            if form.is_valid():
                #encoding_image(name,image)
                form.save()
                encoding_image(str(int(request.POST.get("phone"))),request.FILES["image"])
                return redirect('profiles')
    except:
        messages.error(request,"Try again!add photo and phoneno")
    context={'form':form}
    return render(request,'core/add_profile.html',context)

@login_required
def edit_profile(request,id):
    profile = Profile.objects.get(pk=id)
    form = ProfileForm(instance=profile)
    try:
        if request.method == 'POST':
            form = ProfileForm(request.POST,request.FILES,instance=profile)
            if form.is_valid():
                print(404)
                #encoding_image(name,image)
                form.save()
                try:
                    encoding_image(str(int(request.POST.get("phone"))),request.FILES["image"])
                    #encoding_image(request.POST.get("phone"),request.POST.get("image"))
                    messages.success(request,'update image Sucessfully!')
                except:
                    messages.error(request,'update Sucessfully!')
                return redirect('profiles')
    except:
        messages.error(request,"Try again! add photo and phoneno")
    context={'form':form}
    return render(request,'core/add_profile.html',context)

@login_required
def delete_profile(request,id):
    profile = Profile.objects.get(pk=id)
    profile.delete()
    return redirect('profiles')

@login_required
def clear_history(request):
    history = LastFace.objects.all()
    history.delete()
    return redirect('index')

@login_required
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



# def markAttendance(profile):
#     now = datetime.now()
#     profiles = Profile.objects.all()
#     today = now.strftime("%Y/%m/%d_%H:%M")
#     filename = "media/documents/" + datetime.now().strftime("%Y-%m-%d") + ".csv"
#     print(401)
#     try:
#         print(402)
#         with open(filename, 'a') as f:
#             print(403)
#             print(profile.first_name)
#             #for profile in nameList :
#                 # now = datetime.now()
#                 # dtString = now.strftime('%H:%M:%S')
#                 # f.writelines(f'\n{name},{dtString},{sid_name[sid.index(name)]}')
#             f.writelines(f'\n{profile.first_name},{profile.last_name},{profile.date},{profile.hostelname},{profile.roomno},{profile.phone}')
#             f.close()
#     except:
#         # print(404)
#         # for profile in profiles:
#         #     if profile.present == True:
#         #         profile.present = False
#         #         profile.save()
#         #     else:
#         #         pass
#         # history = LastFace.objects.all()
#         # history.delete()
#         with open(filename, 'w') as f:
#             print(profile.first_name)
#             #for profile in nameList :
#                 # now = datetime.now()
#                 # dtString = now.strftime('%H:%M:%S')
#                 # f.writelines(f'\n{name},{dtString},{sid_name[sid.index(name)]}')
#             print('write')
#             f.writelines(f'first_name,last_name,date,hostelname,roomno,phone')
#             # f.writelines(f'\n{profile.first_name},{profile.last_name},{profile.date},{profile.hostelname},{profile.roomno},{profile.phone}')
#             f.close()

 
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
    print("db sucessfully update!")
    messages.success(request, "attendance db Successfully updated!!")
    return redirect('index')

    
    



def signin(request):
    if request.method == 'POST':
        username = request.POST['username']
        pass1 = request.POST['pass1']
        
        user = authenticate(username=username, password=pass1)
        
        if user is not None:
            login(request, user)
            # fname = user.first_name
            messages.success(request, "Logged In Sucessfully!!")
            # now = datetime.now()
            # filename = "media/documents/" + datetime.now().strftime("%Y-%m-%d") + ".csv"
            # try:
            #     print(402)
            #     f=open(filename, 'r')
            # except:
            #     print(404)
            #     profiles = Profile.objects.all()
            #     with open(filename, 'w') as f:
            #         #for profile in nameList :
            #             # now = datetime.now()
            #             # dtString = now.strftime('%H:%M:%S')
            #             # f.writelines(f'\n{name},{dtString},{sid_name[sid.index(name)]}')
            #         print('write')
            #         f.writelines(f'first_name,last_name,date,hostelname,roomno,phone')
            #         # f.writelines(f'\n{profile.first_name},{profile.last_name},{profile.date},{profile.hostelname},{profile.roomno},{profile.phone}')
            #         f.close()
            #     for profile in profiles:
            #         if profile.present == True:
            #             profile.present = False
            #             profile.save()
            #         else:
            #             pass
            #     history = LastFace.objects.all()
            #     history.delete()
            return render(request, 'core/index.html')
        else:
            messages.error(request, "Bad Credentials!!")
            return redirect('home')
    
    return render(request, 'core/signin.html')

@login_required
def signout(request):
    # absent()
    logout(request)
    messages.success(request, "Logged Out Successfully!!")
    return redirect('home')

def home(request):
    return render(request,'core/open.html')

@login_required
def signup(request):
    if request.method=="POST":
        username=request.POST['username']
        fname = request.POST['fname']
        lname =request.POST['lname']
        # mobileno = request.POST['mobileno']
        pass1 = request.POST['pass1']
        pass2 = request.POST['pass2']
        if User.objects.filter(username=username).exists():
            messages.error(request,"User already exist! try other username....")
            return redirect('home')
        # if User.objects.filter(mobileno=mobileno).exists():
        #     messages.error(request,"mobileno already exist!....")
        #     return redirect('home')
        if len(username)>11:
            messages.error(request,"username must under 11 characters!....")
            return redirect('home')
        if pass1!=pass2:
            messages.error(request,"Passwoed not matched!....")
            return redirect('home')
        myuser = User.objects.create_user(username,None,pass1)
        myuser.lname=lname
        myuser.fname=fname
        myuser.save()  
        return redirect('signin')
        
        
    return render(request, "core/signup.html")


# def absent():
#     # file_path="media/documents/" + datetime.now().strftime("%Y-%m-%d") + ".csv"
#     # dt =pd.read_csv(file_path)
#     # dt=dt.sort_values('hostelname')
#     # list_present_id=dt['phone']
#     file="absentees_documents/" + datetime.now().strftime("%Y-%m-%d") + ".csv"
#     profiles = Profile.objects.all()
#     with open(file, 'w') as f:
#         f.writelines(f'first_name,last_name,date,hostelname,roomno,phone')
#         f.close()
#     for profile in profiles:
#         if profile.present == False:
#             with open(file, 'a') as f:
#                 print(profile.first_name)
#                 f.writelines(f'\n{profile.first_name},{profile.last_name},{profile.date},{profile.hostelname},{profile.roomno},{profile.phone}')
#                 f.close()


@login_required
def download(request):
    print(request.method)
    if request.method=='GET':
        date=request.GET.get("date", "")
        present=request.GET.get("present","")
        hostel=request.GET["hostel"]
        print(date)
        print(present)
        print(hostel)
        if present==None or hostel==None:
            return redirect('index')#####
        #pickle_attenance
        attendance=pickle.loads(open('attendance.pickle',"rb").read())
        print(date)
        print(attendance)
        if date not in attendance.keys():
            messages.success(request,"attendance not found!!")
            return redirect('index')
        att=attendance[str(date)]
        print(att)
        if present=="Absent":
            attendance_list=att[0]
        else:
            attendance_list=att[1]
        file="attendance_documents/" +date+"_"+present+"_"+hostel+"_"+"file.csv"
        profiles = Profile.objects.all()
        with open(file, 'w') as f:
            f.writelines(f'first_name,last_name,date,hostelname,roomno,phone_number')
            f.close()
        if hostel!="All":
            for i in attendance_list:
                profile = Profile.objects.get(pk=i)
                if profile.hostelname == hostel:
                    with open(file, 'a') as f:
                        print(profile.first_name)
                        f.writelines(f'\n{profile.first_name},{profile.last_name},{profile.date},{profile.hostelname},{profile.roomno},{profile.phone}')
                        f.close()
        else:
            for i in attendance_list:
                profile = Profile.objects.get(pk=i)
                with open(file, 'a') as f:
                    print(profile.first_name)
                    f.writelines(f'\n{profile.first_name},{profile.last_name},{profile.date},{profile.hostelname},{profile.roomno},{profile.phone}')
                    f.close()
        dt =pd.read_csv(file)
        # #file based attendance
        # if present=="Absent":
        #     try:
        #         file_path="absentees_documents/" + datetime.now().strftime("%Y-%m-%d") + ".csv"
        #         dt =pd.read_csv(file_path)
        #     except:
        #         messages.error(request, 'file not found.')
        #         return redirect('index')

        # else:
        #     try:
        #         file_path="media/documents/" + datetime.now().strftime("%Y-%m-%d") + ".csv"
        #         dt =pd.read_csv(file_path)
        #     except:
        #         messages.error(request, 'file not found.')
        #         return redirect('index')
        if hostel=="All":
            dt=dt.sort_values('hostelname')
        else:
            dt=dt.sort_values('roomno')
            dt=dt[dt['hostelname']==hostel]
        print(dt)
        dt.to_csv("Downloads/"+date+"_"+present+"_"+hostel+"_"+'file.csv')

        file_server = pathlib.Path("Downloads/"+date+"_"+present+"_"+hostel+"_"+'file.csv')
        if not file_server.exists():
            messages.error(request, 'file not found.')
        else:
            file_to_download = open(str(file_server), 'rb')
            response = FileResponse(file_to_download, content_type='application/force-download')
            response['Content-Disposition'] = 'inline; filename='+date+'"_"'+present+'"_"'+hostel+"_"+'file.csv'
            print(123)
            return response
        
    return redirect('index')
@login_required
def attendance(request):
    return render(request,'core/attendance.html')
@login_required
def manual_checking(request):
    if request.method=='GET':
        phone=request.GET['phone']
        phone=int(phone)
        try:
            profile = Profile.objects.get(pk=phone)
            print(1)
            context = {'profile': profile}
            return render(request,'core/manul_attendance.html',context)
        except:
            print('sorry')
            pass
    return redirect('index')
@login_required
def manual_attendance(request):
    print(2)
    date=datetime.now().strftime("%Y-%m-%d")
    attendance=pickle.loads(open('attendance.pickle',"rb").read())
    print(date)
    print(attendance)
    att=attendance[date]
    if len(att[0])==0:
        return redirect('index')
    if request.method=='POST':
        phone=request.POST['phone']
        phone=int(phone)
        try:
            profile = Profile.objects.get(pk=phone)
            if profile.present!=True and profile.pk not in att[1]:
                profile.present=True
                att[0].remove(profile.pk)
                att[1].append(profile.pk)
                messages.success(request,str(profile.pk)+'present!')
                # markAttendance(profile)
            else:
                messages.success(request,'Already present!')
        except:
            print('sorry')
            messages.success(request,'Sorry! Try Again..')
            pass
    attendance[date]=att
    pickle_file=open('attendance.pickle', 'wb')
    pickle.dump(attendance, pickle_file )
    print("db sucessfully update!")
    return redirect('index')



def pickel_attendance(dte):
    print(404)
    profiles = Profile.objects.all()
    try:
        print(os.path.getsize("attendance.pickle"))
        if os.path.getsize("attendance.pickle") > 0:
            print(1)
            pickle_file = open('attendance.pickle', 'rb')
            print(2)
            pickled_object = pickle.load(pickle_file)

        else:
            pickled_object={}
        if dte  in pickled_object.keys():
            l1=pickled_object[dte]
            if (len(l1[0])+len(l1[1]))==len(profiles):
                return
        attendance_list=[[],[]]
        for profile in profiles:
            attendance_list[0].append(profile.pk)
        pickled_object[dte]=attendance_list
        pickle_file=open('attendance.pickle', 'wb')
        pickle.dump(pickled_object, pickle_file )
        pickle_file.close()
        history = LastFace.objects.all()
        history.delete()
        
    except EOFError:
        # print(pickled_object = pickle.load(pickle_file))
        pickled_object = {}

