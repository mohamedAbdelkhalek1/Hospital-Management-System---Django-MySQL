from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from .consts import *
from .utils import *
import uuid
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _




class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        DOCTOR = 'DOCTOR', 'Doctor'
        NURSE = 'NURSE', 'Nurse'
        PATIENT = 'PATIENT', 'Patient'
    
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True, editable=False)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.ADMIN)


    

        


class Department(models.Model):
    name = models.CharField(max_length=30, verbose_name="القسم",)
    description = models.TextField(verbose_name="وصف القسم")
    head_of_department = models.ForeignKey('Doctor', on_delete=models.CASCADE, null=True, blank=True, related_name='departments_headed')
    department_pic= models.ImageField(default='departments/default/logo.jpg', upload_to=department_directory_path)
    #for return all doctors in department
    def doctors(self):
        return Doctor.objects.filter(department=self)
    #for return all nurses in department
    def nurses(self):
        return Nurse.objects.filter(department=self)
    #for return all medicines in department
    def medicines(self):
        return Medicine.objects.filter(department=self)
    def __str__(self):
        return self.name
    




class Location(models.Model):
    address_1 = models.CharField(max_length=128, blank=True)
    address_2 = models.CharField(max_length=128, blank=True)
    city = models.CharField(max_length=64, default="Cairo")
    governorate  = models.CharField(max_length=100, choices=GOVERNORATE_CHOICES, default="Cairo", verbose_name="المحافظة")
    
    def __str__(self):
        return f"{self.city} - {self.governorate}"



class HospitalUser(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE , unique=True)
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES, default="ذكر")
    location = models.OneToOneField(Location, on_delete=models.SET_NULL, null=True)
    mobile = models.CharField(max_length=20,null=True,blank=True)    
    
    
    @property
    def get_name(self):
        return self.user.first_name+" "+self.user.last_name
    @property
    def get_id(self):
        return self.user.id
    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name} - {self.user.username}'
    class Meta:
        abstract = True




class Doctor(HospitalUser):
    profile_pic= models.ImageField(default='doctors/default/doctor.png', upload_to=doctors_directory_path)
    specialization = models.CharField(max_length=24, choices= DOCTOR_SPECIALIZE_CHOICES, null=True, blank=True, verbose_name='اختصاص الطبيب', default= 'طبيب أخصائي')
    department= models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)

    



class Nurse(HospitalUser):
    profile_pic= models.ImageField(default='nurses/default/nurse.jpg', upload_to=nurses_directory_path)
    department= models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    shift_time=models.CharField(max_length=20, choices=SHIFT_PERIOD_CHOICES,null=True, blank=True, verbose_name=' فترة الدوام', default= 'دوام صباحي')


    



class Patient(HospitalUser):
    profile_pic= models.ImageField(default='patients/default/patient.jpg', upload_to=patients_directory_path)
    symptoms = models.CharField(max_length=100,null=False)
    assigned_doctor = models.ForeignKey('Doctor', on_delete=models.PROTECT, null=True, blank=True, related_name='related_doctor', verbose_name='الدكتور المسؤول')
    admitDate=models.DateField(auto_now=True)
    
    





# remove user location if delete the user
@receiver(post_delete, sender=Doctor)
def delete_doctor_location(sender, instance, *args, **kwargs):
    if instance.location:
        instance.location.delete()
        
@receiver(post_delete, sender=Nurse)
def delete_nurse_location(sender, instance, *args, **kwargs):
    if instance.location:
        instance.location.delete()
        
@receiver(post_delete, sender=Patient)
def delete_patient_location(sender, instance, *args, **kwargs):
    if instance.location:
        instance.location.delete()


class Appointment(models.Model):
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, verbose_name='اسم الحالة')
    department= models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, verbose_name="القسم")
    doctor = models.ForeignKey('Doctor', on_delete=models.CASCADE, verbose_name='الطبيب المعالج')
    appointment_date=models.DateField(default=timezone.now().date() + timezone.timedelta(days=1), verbose_name='تاريخ الكشف	')
    appointment_time=models.CharField(max_length=5, choices=PERIOD_CHOICES, verbose_name='ميعاد الكشف	')
    description=models.TextField(max_length=500, blank=True, null=True, verbose_name='الوصف')
    status=models.BooleanField(default=False)
    is_ready = models.BooleanField(default=False)
    is_done = models.BooleanField(default=False)
    
    def __str__(self):
        return f"أ/ {self.patient} - د/ {self.doctor}"





class Medicine(models.Model):
    name = models.CharField(max_length=255, verbose_name="اسم الدواء")
    description = models.TextField(verbose_name="الوصف")
    quantity = models.PositiveIntegerField(default=0, verbose_name="الكمية المتوافرة")
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="السعر", null=True, blank=True,)
    department= models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, verbose_name="القسم التابع")
    def __str__(self):
        return self.name
    
    
    
    
class PatientDischargeDetails(models.Model):
    appointment = models.OneToOneField('Appointment', on_delete=models.CASCADE, verbose_name=' الحجز الطبي')
    doctor_report = models.TextField(verbose_name="تقرير الطبيب")

    admit_date=models.DateField(auto_now_add=True, verbose_name=' تاريخ تصريح الخروج')

    room_charge=models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name=" حساب الغرفة")
    medicine_cost=models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name=" حساب الدواء")
    doctor_fee=models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name=" رسوم الطبيب ")
    other_charge=models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name=" رسوم أخرى")
    is_paid=models.BooleanField(default=False)
    
    @property
    def total(self):
        total_value = 0
        total_value += self.room_charge+ self.medicine_cost+ self.doctor_fee+ self.other_charge
        return total_value
    
    def __str__(self):
        return f"{self.appointment} -- اجمالي الدفع :{self.total}"


# User Signals

# Create user profile if create user 
# update user role if update
@receiver(post_save, sender=User)
def create_user_model(sender, instance, created, **kwargs):
    if created:
        if instance.role == 'DOCTOR':
            doctor = Doctor.objects.create(user=instance)
            doctor.location = Location.objects.create()
            doctor.save()
        elif instance.role == 'NURSE':
            nurse = Nurse.objects.create(user=instance)
            nurse.location = Location.objects.create()
            nurse.save()
        elif instance.role == 'PATIENT':
            patient = Patient.objects.create(user=instance)
            patient.location = Location.objects.create()
            patient.save()
    else:
        if instance.role == 'DOCTOR':
            if Nurse.objects.filter(user=instance).exists():
                Nurse.objects.get(user= instance).delete()
                doctor = Doctor.objects.create(user=instance)
                doctor.location = Location.objects.create()
                doctor.save()
            elif Patient.objects.filter(user=instance).exists():
                Patient.objects.get(user= instance).delete()
                doctor = Doctor.objects.create(user=instance)
                doctor.location = Location.objects.create()
                doctor.save()
            
        elif instance.role == 'NURSE':
            if Doctor.objects.filter(user=instance).exists():
                Doctor.objects.get(user= instance).delete()
                nurse = Nurse.objects.create(user=instance)
                nurse.location = Location.objects.create()
                nurse.save()
            elif Patient.objects.filter(user=instance).exists():
                Patient.objects.get(user= instance).delete()
                Doctor.objects.get(user= instance).delete()
                nurse = Nurse.objects.create(user=instance)
                nurse.location = Location.objects.create()
                nurse.save()
            
        elif instance.role == 'PATIENT':
            if Nurse.objects.filter(user=instance).exists():
                Nurse.objects.get(user= instance).delete()
                patient = Patient.objects.create(user=instance)
                patient.location = Location.objects.create()
                patient.save()
            elif Doctor.objects.filter(user=instance).exists():
                Doctor.objects.get(user= instance).delete()
                patient = Patient.objects.create(user=instance)
                patient.location = Location.objects.create()
                patient.save()
            
    