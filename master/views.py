import os
from django.utils.http import urlencode
from django.conf import settings
from xhtml2pdf import pisa
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UsernameField, PasswordChangeForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.views import View
from django.template.loader import get_template
from.forms import *
from .filters import *
from django.core.mail import send_mail
from . import bones_classifier,brain_classifier,skin_classifier
from PIL import Image
import io
import base64



#custom the UserCreationForm to update the auth user in it
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name")
        field_classes = {"username": UsernameField}



# Create your views here.
def home_view(request):
    departments = Department.objects.all()
    return render(request, 'home.html', {'departments':departments})


#-----------for checking user is doctor , patient or admin(by submit)
def is_admin(user):
    return True if user.role =='ADMIN' else False
def is_doctor(user):
    return True if user.role =='DOCTOR' else False
def is_nurse(user):
    return True if user.role =='NURSE' else False
def is_patient(user):
    return True if user.role =='PATIENT' else False


def login_view(request, hospital_user):
    if request.method == "POST":
        login_form = AuthenticationForm(request=request, data=request.POST)
        if login_form.is_valid():
            username = login_form.cleaned_data.get('username')
            password = login_form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if is_admin(user):
                    if user.is_staff:
                        login(request, user)
                        messages.success(request, f"You are logged successfully as {user.username}.")
                        return redirect('after_login')
                    else:
                        messages.warning(request, f"Sorry, your account has not been confirmed yet.")
                        return redirect('home')
                else:
                    if user.is_active:
                        login(request, user)
                        messages.success(request, f"You are logged successfully as {user.username}.")
                        return redirect('after_login')
                    else:
                        messages.warning(request, f"Sorry, your account has not been confirmed yet.")
                        return redirect('home')
            else:
                messages.warning(request, f"An error occured trying to login.")
        else:
            messages.warning(request, f"An error occured trying to login.")
    elif request.method == "GET":
        login_form = AuthenticationForm()
    return render(request, 'login.html', {"login_form":login_form, "hospital_user":hospital_user})



@login_required
def logout_view(request):
    logout(request)
    messages.warning(request, f"You are logged out and you are now without an account")
    return redirect('home')


def register_view(request, hospital_user):
    if request.method == 'POST':
        register_form = CustomUserCreationForm(data=request.POST)
        if register_form.is_valid():
            user = register_form.save(commit=False)
            user.role = hospital_user
            user.is_active = False
            user.save()
            user.refresh_from_db()
            messages.success(request, f"Your data has been registered successfully. You can log in as {user.username} after confirming your account within 24 hours.")
            return redirect("home")
        else:
            messages.error(request, f"An error occured try again.")
    elif request.method == 'GET':
        register_form = CustomUserCreationForm()
    return render(request, 'register.html', {'register_form':register_form, 'hospital_user':hospital_user})







#---------AFTER ENTERING CREDENTIALS WE CHECK WHETHER USERNAME AND PASSWORD IS OF ADMIN,DOCTOR OR PATIENT
@login_required
def after_login_view(request):
    if is_admin(request.user):
        return redirect('admin_dashboard')
    elif is_doctor(request.user):
        return redirect('doctor_dashboard')
    elif is_nurse(request.user):
        return redirect('nurse_dashboard')
    elif is_patient(request.user):
        return redirect('patient_dashboard')




@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class AdminProfileView(View):
    def get(self, request):
        user_form = UserForm(instance=request.user)
        return render(request, 'after_login/admin_profile.html', {'user_form':user_form})
    
    def post(self, request):
        user_form = UserForm(request.POST, instance=request.user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, 'Profile Updated')
            return redirect("admin_profile")
        else:
            messages.warning(request, 'Error Updating Profile')
        return render(request, 'after_login/admin_profile.html', {'user_form':user_form})
        




@method_decorator(login_required, name='dispatch')
class UserProfileView(View):
    def get(self, request):
        user_form = UserForm(instance=request.user)
        if is_doctor(request.user):
            profile_form = DoctorForm(instance=request.user.doctor)
            location_form = LocationForm(instance=request.user.doctor.location)
        elif is_nurse(request.user):
            profile_form = NurseForm(instance=request.user.nurse)
            location_form = LocationForm(instance=request.user.nurse.location)
        elif is_patient(request.user):
            profile_form = PatientForm(instance=request.user.patient)
            location_form = LocationForm(instance=request.user.patient.location)
        
        return render(request, 'after_login/user_profile.html',
                      {'user_form':user_form, 'profile_form':profile_form, 'location_form':location_form})
    
    def post(self, request):
        user_form = UserForm(request.POST, instance=request.user)
        if is_doctor(request.user):
            profile_form = DoctorForm(request.POST, request.FILES, instance=request.user.doctor)
            location_form = LocationForm(request.POST, instance=request.user.doctor.location)
        elif is_nurse(request.user):
            profile_form = NurseForm(request.POST, request.FILES, instance=request.user.nurse)
            location_form = LocationForm(request.POST, instance=request.user.nurse.location)
        elif is_patient(request.user):
            profile_form = PatientForm(request.POST, request.FILES, instance=request.user.patient)
            location_form = LocationForm(request.POST, instance=request.user.patient.location)
        if user_form.is_valid() and profile_form.is_valid() and location_form.is_valid():
            user_form.save()
            profile_form.save()
            location_form.save()
            messages.success(request, 'Profile Updated')
            return redirect("user_profile")
        else:
            messages.warning(request, 'Error Updating Profile')
        return render(request, 'after_login/user_profile.html',
                      {'user_form':user_form, 'profile_form':profile_form, 'location_form':location_form})
        

@login_required
def change_password_view(request):
    if request.method == 'POST':
        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            messages.success(request, f"Password Is Updated Successfully")
            if is_admin(request.user):
                return redirect("admin_profile")
            else:
                return redirect("user_profile")
        else:
            messages.warning(request, 'Error Updating Password Try Again')
    else:
        password_form = PasswordChangeForm(user=request.user)
    return render(request, 'after_login/change_password.html', {"password_form": password_form})





#---------------------------------------------------------------------------------
#------------------------ ADMIN RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required()
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    #for both table in admin dashboard
    doctors=Doctor.objects.all().order_by('-id')
    departments=Department.objects.all().order_by('-id')
    medicines=Medicine.objects.all().order_by('-id')
    nurses=Nurse.objects.all().order_by('-id')
    patients=Patient.objects.all().order_by('-id')
    #for three cards
    doctorcount=Doctor.objects.all().filter(user__is_active=True).count()
    pendingdoctorcount=Doctor.objects.all().filter(user__is_active=False).count()
    
    departmentcount=Department.objects.all().count()
    medicinecount=Medicine.objects.all().count()

    
    nursecount=Nurse.objects.all().filter(user__is_active=True).count()
    pendingnursecount=Nurse.objects.all().filter(user__is_active=False).count()

    patientcount=Patient.objects.all().filter(user__is_active=True).count()
    pendingpatientcount=Patient.objects.all().filter(user__is_active=False).count()

    appointmentcount=Appointment.objects.all().filter(status=True, is_done=False).count()
    pendingappointmentcount=Appointment.objects.all().filter(status=False).count()
    
    mydict={
    'doctors':doctors,
    'medicines':medicines,
    'departments':departments,
    'nurses':nurses,
    'patients':patients,
    'doctorcount':doctorcount,
    'pendingdoctorcount':pendingdoctorcount,
    'departmentcount':departmentcount,
    'medicinecount':medicinecount,
    'nursecount':nursecount,
    'pendingnursecount':pendingnursecount,
    'patientcount':patientcount,
    'pendingpatientcount':pendingpatientcount,
    'appointmentcount':appointmentcount,
    'pendingappointmentcount':pendingappointmentcount,
    }
    return render(request,'after_login/admin_dashboard.html',context=mydict)




@login_required
@user_passes_test(is_admin)
def admin_manager_view(request, data):
    if data == 'MEDICINE':
        medicines = Medicine.objects.all().order_by('-id')
        data_table = MedicineFilter(request.GET, medicines)
    elif data == 'DEPARTMENT':
        departments = Department.objects.all().order_by('-id')
        data_table = DepartmentFilter(request.GET, departments)
    elif data == 'DOCTOR':
        doctors = Doctor.objects.all().order_by('-id')
        data_table = DoctorFilter(request.GET, doctors)
    elif data == 'NURSE':
        nurses = Nurse.objects.all().order_by('-id')
        data_table = NurseFilter(request.GET, nurses)
    elif data == 'PATIENT':
        patients = Patient.objects.all().order_by('-id')
        data_table = PatientFilter(request.GET, patients)
    elif data == 'APPOINTMENT':
        appointments = Appointment.objects.all().order_by('-id')
        data_table = AppointmentFilter(request.GET, appointments)
        
    context = {'data_table': data_table, 'data_name' : data}
    return render(request, 'after_login/admin_manager.html', context)



@login_required
@user_passes_test(is_admin)
def admin_confirm_user_view(request, id):
    user=User.objects.get(id=id)
    role = user.role
    user.is_active = True
    user.save()
    messages.success(request, f"The user {user.username} has been successfully confirmed as a {role}.")
    return redirect('admin_manager', data=role)


@login_required
@user_passes_test(is_admin)
def admin_delete_user_view(request, id):
    user=User.objects.get(id=id)
    role = user.role
    user.delete()
    messages.warning(request, f"The user has been deleted from the hospital database.")
    return redirect('admin_manager', data=role)



@login_required
@user_passes_test(is_admin)
def admin_delete_department_view(request, id):
    department=Department.objects.get(id=id)
    department.delete()
    messages.warning(request, f"The department has been deleted from the hospital database.")
    return redirect('admin_manager', data='DEPARTMENT')


@login_required
@user_passes_test(is_admin)
def admin_delete_medicine_view(request, id):
    medicine=Medicine.objects.get(id=id)
    medicine.delete()
    messages.warning(request, f"The medication has been deleted from the hospital database.")
    return redirect('admin_manager', data='MEDICINE')



@login_required
@user_passes_test(is_admin)
def admin_add_user_view(request, hospital_user):
    if request.method == 'POST':
        user_form = CustomUserCreationForm(data=request.POST)
        if user_form.is_valid():
            user = user_form.save(commit=False)
            user.role = hospital_user
            if hospital_user=='ADMIN':
                user.is_staff = True
                user.save()
                user.refresh_from_db()
                messages.success(request, f"The user {user.username} has been successfully added as a {hospital_user}.")
                return redirect('admin_dashboard')
            else:
                user.save()
                user.refresh_from_db()
                messages.success(request, f"The user {user.username} has been successfully added as a {hospital_user}.")
                return redirect('admin_manager', data=hospital_user)
        else:
            messages.error(request, f"An error occured try again.")
    elif request.method == 'GET':
        user_form = CustomUserCreationForm()
    return render(request, 'after_login/admin_add_user.html', {'user_form':user_form, 'hospital_user':hospital_user})



@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class AdminUpdateUserView(View):
    def get(self, request, id):
        user=User.objects.get(id=id)
        if is_doctor(user):
            form = AdminDoctorForm(instance=user.doctor)
        elif is_nurse(user):
            form = AdminNurseForm(instance=user.nurse)
        return render(request, 'after_login/admin_update_user.html',{'form':form})
    
    def post(self, request, id):
        user=User.objects.get(id=id)
        if is_doctor(user):
            form = AdminDoctorForm(request.POST, instance=user.doctor)
        elif is_nurse(user):
            form = AdminNurseForm(request.POST, instance=user.nurse)
        if form.is_valid():
            form.save()
            messages.success(request, f'{user.role} Updated')
            return redirect("admin_update_user", id=id)
        else:
            messages.warning(request, f'Error Updating {user.role}')
        return render(request, 'after_login/admin_update_user.html',{'form':form})
        




@login_required
@user_passes_test(is_admin)
def admin_add_medicine_view(request):
    if request.method == 'POST':
        medicine_form = MedicineForm(request.POST)
        if medicine_form.is_valid():
            medicine = medicine_form.save()
            messages.success(request, f"The medicine {medicine.name} has been added successfully.")
            return redirect('admin_manager', data='MEDICINE')
        else:
            messages.warning(request, f"An error occured try again.")
    elif request.method == 'GET':
        medicine_form = MedicineForm()
    return render(request, 'after_login/admin_medicine.html', {'medicine_form':medicine_form})




@login_required
@user_passes_test(is_admin)
def admin_update_medicine_view(request, id):
    if request.method == 'POST':
        medicine_form = MedicineForm(request.POST, instance=Medicine.objects.get(id=id))
        if medicine_form.is_valid():
            medicine = medicine_form.save()
            messages.success(request, f"The medicine {medicine.name} has been updated successfully.")
            return redirect('admin_manager', data='MEDICINE')
        else:
            messages.warning(request, f"An error occured try again.")
    elif request.method == 'GET':
        medicine_form = MedicineForm(instance=Medicine.objects.get(id=id))
    return render(request, 'after_login/admin_medicine.html', {'medicine_form':medicine_form})


@login_required
@user_passes_test(is_admin)
def admin_add_department_view(request):
    if request.method == 'POST':
        department_form = DepartmentForm(request.POST, request.FILES)
        if department_form.is_valid():
            department = department_form.save()
            messages.success(request, f"The department {department.name} has been added successfully.")
            return redirect('admin_manager', data='DEPARTMENT')
        else:
            messages.warning(request, f"An error occured try again.")
    elif request.method == 'GET':
        department_form = DepartmentForm()
    return render(request, 'after_login/admin_department.html', {'department_form':department_form})




@login_required
@user_passes_test(is_admin)
def admin_update_department_view(request, id):
    if request.method == 'POST':
        department_form = DepartmentForm(request.POST, request.FILES, instance=Department.objects.get(id=id))
        if department_form.is_valid():
            department = department_form.save()
            messages.success(request, f"The department {department.name} has been updated successfully.")
            return redirect('admin_manager', data='DEPARTMENT')
        else:
            messages.warning(request, f"An error occured try again.")
    elif request.method == 'GET':
        department_form = DepartmentForm(instance=Department.objects.get(id=id))
    return render(request, 'after_login/admin_department.html', {'department_form':department_form})


@login_required
@user_passes_test(is_admin)
def admin_add_appointment_view(request):
    if request.method == 'POST':
        appointment_form = AppointmentForm(request.POST)
        if appointment_form.is_valid():
            appointment = appointment_form.save(commit=False)
            appointment.status = True
            appointment.save()
            messages.success(request, f"The appointment has been successfully.")
            return redirect('admin_manager', data='APPOINTMENT')
        else:
            messages.warning(request, f"An error occured try again.")
    elif request.method == 'GET':
        appointment_form = AppointmentForm()
    return render(request, 'after_login/admin_appointment.html', {'appointment_form':appointment_form})



@login_required
@user_passes_test(is_admin)
def admin_confirm_appointment_view(request, id):
    appointment=Appointment.objects.get(id=id)
    appointment.status = True
    appointment.save()
    messages.success(request, f"The appointment has been successfully confirmed.")
    return redirect('admin_manager', data='APPOINTMENT')



@login_required
@user_passes_test(is_admin)
def admin_delete_appointment_view(request, id):
    appointment=Appointment.objects.get(id=id)
    appointment.delete()
    messages.warning(request, f"The appointment has been deleted from the hospital database.")
    return redirect('admin_manager', data='APPOINTMENT')



@login_required
@user_passes_test(is_admin)
def admin_discharge_patient_view(request, id):
    appointment = Appointment.objects.get(id= id)
    if request.method == 'POST':
        discharge_form = PatientDischargeForm(request.POST, instance=PatientDischargeDetails.objects.get(appointment=appointment))
        if discharge_form.is_valid():
            form = discharge_form.save(commit= False)
            form.discharge_status = True
            form.save()
            appointment.is_done=True
            appointment.save()
            messages.success(request, f'The exit permit was successfully issued')
            return redirect('final_discharge', id=id)
        else:
            messages.error(request, f"An error occured try again.")
    elif request.method == 'GET':
        discharge_form = PatientDischargeForm(instance=PatientDischargeDetails.objects.get(appointment=appointment))
    return render(request, 'after_login/admin_discharge_patient.html', {'discharge_form': discharge_form})




@login_required
def final_discharge_view(request, id):
    appointment = Appointment.objects.get(id= id)
    discharge_details = PatientDischargeDetails.objects.get(appointment= appointment)
    return render(request, 'after_login/final_discharge.html', {'discharge_form': discharge_details})


@login_required
def pay_discharge_view(request, id):
    discharge_form = PatientDischargeDetails.objects.get(id= id)
    discharge_form.is_paid = True
    discharge_form.save()
    messages.success(request, f'The permit costs have been paid successfully')
    if is_admin(request.user):
        return redirect('admin_manager', data='APPOINTMENT')
    elif is_patient(request.user):
        return redirect("patient_appointment")
    


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = io.BytesIO()
    # تحويل صفحة HTML إلى ملف PDF باستخدام pisa
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result, encoding="UTF-8")
    if not pdf.err:
        return result.getvalue()
    return None


@login_required
def download_permit_pdf(request, id):
    discharge_details = PatientDischargeDetails.objects.get(id=id)
    context = {'discharge_form': discharge_details}
    pdf = render_to_pdf('after_login/download_bill.html', context)

    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="permit.pdf"'
        # response.write(pdf_content)
        return response

    # If there is an error generating the PDF, you can handle it here
    return HttpResponse('Error generating PDF', status=500)



def department_view(request, id):
    try:
        department = Department.objects.get(id=id)
        if department is None:
            raise Exception
        return render(request, 'services/department.html', {'department':department})
    except Exception as e:
        messages.warning(request, f'Invalid {id} id')
        return redirect('home')
    
    



#---------------------------------------------------------------------------------
#------------------------ DOCTOR RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required
@user_passes_test(is_doctor)
def doctor_dashboard_view(request):
    department = request.user.doctor.department
    nurses = Nurse.objects.filter(user__is_active=True, department=department)
    patients = Patient.objects.filter(user__is_active=True, assigned_doctor=request.user.doctor)
    
    nurse_count = nurses.count()
    patient_count = patients.count()
    appointment_count = Appointment.objects.filter(
        status=True, doctor=request.user.doctor, appointment_date=timezone.now().date()).count()
    
    context = {
        'department':department,
        'nurses': nurses,
        'patients': patients,
        'nurse_count': nurse_count,
        'patient_count': patient_count,
        'appointment_count': appointment_count,
    }
    
    return render(request, 'after_login/doctor_dashboard.html', context)



@login_required
@user_passes_test(is_doctor)
def doctor_appointment_view(request):
    appointments = Appointment.objects.filter(status=True, is_ready=False, doctor=request.user.doctor)
    appointment_data = AppointmentFilter(request.GET, appointments)
    return render(request, 'after_login/doctor_appointment.html', {'appointments': appointment_data})



@login_required
@user_passes_test(is_doctor)
def doctor_report_view(request, id):
    appointment = Appointment.objects.get(id= id)
    if request.method == 'POST':
        discharge_form = DoctorPatientDischargeForm(request.POST)
        if discharge_form.is_valid():
            form = discharge_form.save(commit=False)
            form.appointment = appointment
            form.save()
            appointment.is_ready=True
            appointment.save()
            messages.success(request, f'The report has been sent successfully')
            return redirect('doctor_appointment')
        else:
            messages.error(request, f"An error occured try again.")
    elif request.method == 'GET':
        discharge_form = DoctorPatientDischargeForm()
    return render(request, 'after_login/doctor_report.html', {'discharge_form': discharge_form})



#---------------------------------------------------------------------------------
#------------------------ NURSE RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required
@user_passes_test(is_nurse)
def nurse_dashboard_view(request):
    department = request.user.nurse.department
    nurses = Nurse.objects.filter(user__is_active=True, department=department)
    doctors = Doctor.objects.filter(user__is_active=True, department=department)
    appointments = Appointment.objects.filter(status=True, department=department, appointment_date=timezone.now().date())
    
    nurse_count = nurses.count()
    doctor_count = doctors.count()
    appointment_count = appointments.count()
    
    context = {
        'department': department,
        'nurses': nurses,
        'doctors': doctors,
        'nurse_count': nurse_count,
        'doctor_count': doctor_count,
        'appointment_count': appointment_count,
    }
    
    return render(request, 'after_login/nurse_dashboard.html', context)



@login_required
@user_passes_test(is_nurse)
def nurse_appointment_view(request):
    department = request.user.nurse.department
    appointments = Appointment.objects.filter(status=True, department=department)
    appointment_data = AppointmentFilter(request.GET, appointments)
    return render(request, 'after_login/nurse_appointment.html', {'appointments': appointment_data})





#---------------------------------------------------------------------------------
#------------------------ PATIENT RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required
@user_passes_test(is_patient)
def patient_dashboard_view(request):
    doctor = request.user.patient.assigned_doctor
    
    appointment_count = Appointment.objects.filter(
        status=True, patient=request.user.patient, appointment_date=timezone.now().date()).count()
    past_appointment_count = Appointment.objects.filter(
        status=True, patient=request.user.patient, appointment_date__lt=timezone.now().date()).count()
    future_appointment_count = Appointment.objects.filter(
        status=True, patient=request.user.patient, appointment_date__gt=timezone.now().date()).count()
    
    context = {
        'doctor': doctor,
        'appointment_count': appointment_count,
        'past_appointment_count': past_appointment_count,
        'future_appointment_count': future_appointment_count,
    }
    
    return render(request, 'after_login/patient_dashboard.html', context)



@login_required
@user_passes_test(is_patient)
def patient_appointment_view(request):
    appointments = Appointment.objects.filter(patient=request.user.patient)
    appointment_data = AppointmentFilter(request.GET, appointments)
    return render(request, 'after_login/patient_appointment.html', {'appointments': appointment_data})



@login_required
@user_passes_test(is_patient)
def patient_update_appointment_view(request, id):
    if request.method == 'POST':
        appointment_form = AppointmentForm(request.POST, instance=Appointment.objects.get(id=id))
        if appointment_form.is_valid():
            appointment = appointment_form.save(commit=False)
            appointment.status = False
            appointment.save()
            messages.success(request, f"The appointment has been updated successfully and will be confirmed.")
            return redirect('patient_appointment')
        else:
            messages.error(request, f"An error occured try again.")
    elif request.method == 'GET':
        appointment_form = AppointmentForm(instance=Appointment.objects.get(id=id))
    return render(request, 'after_login/book_appointment.html', {'appointment_form':appointment_form})



@login_required
@user_passes_test(is_patient)
def patient_delete_appointment_view(request, id):
    appointment=Appointment.objects.get(id=id)
    appointment.delete()
    messages.warning(request, f"The appointment has been deleted.")
    return redirect('patient_appointment')




@login_required
def book_appointment_view(request):
    if request.method == 'POST':
        appointment_form = AppointmentForm(request.POST)
        if appointment_form.is_valid():
            appointment = appointment_form.save()
            messages.success(request, f"The reservation has been added successfully and will be confirmed.")
            if is_doctor(request.user):
                return redirect('doctor_dashboard')
            elif is_nurse(request.user):
                return redirect('nurse_dashboard')
            elif is_patient(request.user):
                return redirect('patient_dashboard')
        else:
            messages.error(request, f"An error occured try again.")
    elif request.method == 'GET':
        appointment_form = AppointmentForm()
    return render(request, 'after_login/book_appointment.html', {'appointment_form':appointment_form})
    



def medicine_view(request):
    medicines = Medicine.objects.all().order_by('name')
    medicine_filter = MedicineFilter(request.GET, medicines)
    return render(request, 'services/medicine.html', {'medicines':medicine_filter})


def aboutus_view(request):
    departments = Department.objects.all().order_by('name')
    return render(request, 'services/aboutus.html', {'departments':departments})



@login_required
def contactus_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=request.user)
        if form.is_valid():
            message = form.cleaned_data['message']
            email_subject = f"Contact Form Submission from {request.user.username}"
            email_message = f"Name: {request.user.first_name} {request.user.last_name}\nEmail: {request.user.email}\nMessage: {message}"
            try:
                send_mail(email_subject, email_message, request.user.username, [settings.EMAIL_HOST_USER], fail_silently=True)
                messages.success(request, 'Your message has been sent!')
            except Exception as e:
                print(e)
                messages.error(request, 'An error occurred. Please try again.')
        else:
            messages.error(request, 'An error occurred. Please try again.')
    else:
        form = ContactForm(instance=request.user)
    return render(request, 'after_login/contactus.html', {'form':form})




@login_required
def send_mail_view(request, id):
    receiver = User.objects.get(id= id)
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=request.user)
        if form.is_valid():
            message = form.cleaned_data['message']
            email_subject = f"Contact Form Submission from {request.user.role}/ {request.user.username}"
            email_message = f"Name: {request.user.first_name} {request.user.last_name}\nEmail: {request.user.email}\nMessage: {message}"
            try:
                send_mail(email_subject, email_message, request.user.username, [receiver.email], fail_silently=True)
                messages.success(request, 'Your message has been sent!')
            except Exception as e:
                print(e)
                messages.error(request, 'An error occurred. Please try again.')
        else:
            messages.error(request, 'An error occurred. Please try again.')
    else:
        form = ContactForm(instance=request.user)
    return render(request, 'after_login/contactus.html', {'form':form})




#---------------------------------------------------------------------------------
#------------------------ AI RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------

#ai model 

def skin_detect_view(request):
    if request.method == 'POST' and request.FILES['image']:
        image = request.FILES['image']
        image_path = 'E:/bulding/Django_projects/Hospital/master/static/images' # اسم الملف الذي سيتم حفظه
        img = Image.open(io.BytesIO(image.read()))

        # تحويل الصورة إلى PNG
        image_path += ".png"
        img.save(image_path, format='PNG')
        
        # تحميل النموذج والتصنيف
        model_path = 'E:/bulding/Django_projects/Hospital/master/ai/model.h5'
        model, input_layer = skin_classifier.load_trained_model(model_path)
        idx, pred = skin_classifier.classifier(image_path, model, input_layer)
        
        # تحديد الفئة الناتجة عن التصنيف
        classes =['actinic keratosis', 'basal cell carcinoma', 'dermatofibroma', 'melanoma', 'nevus', 'pigmented benign keratosis \n ', 'seborrheic keratosis', 'squamous cell carcinoma', 'vascular lesion']
        result = classes[idx]
        
        # تحويل الصورة إلى base64
        img = Image.open(image_path)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

        res = {"result": result, "image": img_str}
        return render(request, 'ai_classifier/skin_detect.html', {'res': res})
    return render(request, 'ai_classifier/skin_detect.html')



def bones_detect_view(request):
    if request.method == 'POST' and request.FILES['image']:
        image = request.FILES['image']
        image_path = 'E:/bulding/Django_projects/Hospital/master/static/images' # اسم الملف الذي سيتم حفظه
        img = Image.open(io.BytesIO(image.read()))

        # تحويل الصورة إلى PNG
        image_path += ".png"
        img.save(image_path, format='PNG')
        
        # تحميل النموذج والتصنيف
        model_path = 'E:/bulding/Django_projects/Hospital/master/ai/xray.h5'
        model, input_layer = bones_classifier.load_trained_model(model_path)
        idx, pred = bones_classifier.classifier(image_path, model, input_layer)
        
        # تحديد الفئة الناتجة عن التصنيف
        classes=['No fracture', 'fractured']
        index = int(pred) 
        result = classes[index]
        
        # تحويل الصورة إلى base64
        img = Image.open(image_path)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

        res = {"result": result, "image": img_str}
        return render(request, 'ai_classifier/bones_classifier.html', {'res': res})
    return render(request, 'ai_classifier/bones_classifier.html')



def brain_detect_view(request):
    if request.method == 'POST' and request.FILES['image']:
        image = request.FILES['image']
        image_path = 'E:/bulding/Django_projects/Hospital/master/static/images' # اسم الملف الذي سيتم حفظه
        img = Image.open(io.BytesIO(image.read()))

        # تحويل الصورة إلى PNG
        image_path += ".png"
        img.save(image_path, format='PNG')
        
        # تحميل النموذج والتصنيف
        model_path = 'E:/bulding/Django_projects/Hospital/master/ai/brain.h5'
        model, input_layer = brain_classifier.load_trained_model(model_path)
        idx, pred = brain_classifier.classifier(image_path, model, input_layer)
        
        # تحديد الفئة الناتجة عن التصنيف
        classes=['No tumor', 'Stable tumor', 'Unstable tumor']
        index = int(pred*10/3.34) # to get from 0 to 2 to choose a suitable choise
        result = classes[index]
        
        # تحويل الصورة إلى base64
        img = Image.open(image_path)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

        res = {"result": result, "image": img_str}
        return render(request, 'ai_classifier/brain_classifier.html', {'res': res})
    return render(request, 'ai_classifier/brain_classifier.html')
