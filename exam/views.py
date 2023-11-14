from django.shortcuts import render, redirect, reverse
from . import forms, models
from django.db.models import Sum
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from datetime import date, timedelta
from django.db.models import Q
from django.core.mail import send_mail
from teacher import models as TMODEL
from student import models as SMODEL
from teacher import forms as TFORM
from student import forms as SFORM
from exam import models as QMODEL
from django.contrib.auth.models import User


def home_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect("afterlogin")
    return render(request, "exam/index.html")


def is_teacher(user):
    return user.groups.filter(name="TEACHER").exists()


def is_student(user):
    return user.groups.filter(name="STUDENT").exists()


def afterlogin_view(request):
    if is_student(request.user):
        return redirect("student/student-dashboard")

    elif is_teacher(request.user):
        accountapproval = TMODEL.Teacher.objects.all().filter(
            user_id=request.user.id, status__in=[True]
        )
        if accountapproval:
            return redirect("teacher/teacher-dashboard")
        else:
            return render(request, "teacher/teacher_wait_for_approval.html")
    else:
        return redirect("admin-dashboard")


def adminclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect("afterlogin")
    return HttpResponseRedirect("adminlogin")


@login_required(login_url="adminlogin")
def admin_dashboard_view(request):
    dict = {
        "total_student": SMODEL.Student.objects.all().count(),
        "total_teacher": TMODEL.Teacher.objects.all().count(),
        "total_course": models.Course.objects.all().count(),
        "total_question": models.Question.objects.all().count(),
    }
    return render(request, "exam/admin_dashboard.html", context=dict)


@login_required(login_url="admin-view-student")
def admin_view_student(request):
    students = SMODEL.Student.objects.all()
    return render(request, "exam/admin_view_student.html", {"students": students})


@login_required(login_url="adminlogin")
def admin_teacher_view(request):
    print(TMODEL.Teacher.objects.filter(status__in=[False]).all())

    dict = {
        "total_teacher": TMODEL.Teacher.objects.filter(status__in=[True]).count(),
        "pending_teacher": TMODEL.Teacher.objects.filter(status__in=[False]).count(),
        "salary": TMODEL.Teacher.objects.filter(status__in=[True]).aggregate(
            Sum("salary")
        )["salary__sum"],
    }
    return render(request, "exam/admin_teacher.html", context=dict)


@login_required(login_url="adminlogin")
def admin_view_teacher_view(request):
    teachers = TMODEL.Teacher.objects.all().filter(status__in=[True])
    return render(request, "exam/admin_view_teacher.html", {"teachers": teachers})


@login_required(login_url="adminlogin")
def update_teacher_view(request, pk):
    teacher = TMODEL.Teacher.objects.get(id=pk)
    user = TMODEL.User.objects.get(id=teacher.user_id)
    userForm = TFORM.TeacherUserForm(instance=user)
    teacherForm = TFORM.TeacherForm(request.FILES, instance=teacher)
    mydict = {"userForm": userForm, "teacherForm": teacherForm}
    if request.method == "POST":
        userForm = TFORM.TeacherUserForm(request.POST, instance=user)
        teacherForm = TFORM.TeacherForm(request.POST, request.FILES, instance=teacher)
        if userForm.is_valid() and teacherForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            teacherForm.save()
            return redirect("admin-view-teacher")
    return render(request, "exam/update_teacher.html", context=mydict)


@login_required(login_url="adminlogin")
def delete_teacher_view(request, pk):
    teacher = TMODEL.Teacher.objects.get(id=pk)
    user = User.objects.get(id=teacher.user_id)
    courses = QMODEL.Course.objects.all().filter(teacher=teacher)
    involvements = QMODEL.TeacherStudentInvolvement.objects.all().filter(teacher=teacher)
    for i in involvements:
        i.delete()
    for course in courses:
        questions = QMODEL.Question.objects.all().filter(course=course)
        results = QMODEL.Result.objects.all().filter(exam=course)
        for q in questions:
            q.delete()
        for r in results:
            r.delete()
        course.delete()
    teacher.delete()
    user.delete()
    return HttpResponseRedirect("/admin-view-teacher")


@login_required(login_url="adminlogin")
def admin_view_pending_teacher_view(request):
    teachers = TMODEL.Teacher.objects.all().filter(status__in=[False])
    return render(
        request, "exam/admin_view_pending_teacher.html", {"teachers": teachers}
    )


@login_required(login_url="adminlogin")
def approve_teacher_view(request, pk):
    teacherSalary = forms.TeacherSalaryForm()
    if request.method == "POST":
        teacherSalary = forms.TeacherSalaryForm(request.POST)
        if teacherSalary.is_valid():
            teacher = TMODEL.Teacher.objects.get(id=pk)
            teacher.salary = teacherSalary.cleaned_data["salary"]
            teacher.status = True
            teacher.save()
        else:
            print("form is invalid")
        return HttpResponseRedirect("/admin-view-pending-teacher")
    return render(request, "exam/salary_form.html", {"teacherSalary": teacherSalary})


@login_required(login_url="adminlogin")
def reject_teacher_view(request, pk):
    teacher = TMODEL.Teacher.objects.get(id=pk)
    user = User.objects.get(id=teacher.user_id)
    user.delete()
    teacher.delete()
    return HttpResponseRedirect("/admin-view-pending-teacher")


@login_required(login_url="adminlogin")
def admin_view_teacher_salary_view(request):
    teachers = TMODEL.Teacher.objects.all().filter(status__in=[True])
    return render(
        request, "exam/admin_view_teacher_salary.html", {"teachers": teachers}
    )


@login_required(login_url="adminlogin")
def update_student_view(request, pk):
    student = SMODEL.Student.objects.get(id=pk)
    user = SMODEL.User.objects.get(id=student.user_id)
    userForm = SFORM.StudentUserForm(instance=user)
    studentForm = SFORM.StudentForm(request.FILES, instance=student)
    mydict = {"userForm": userForm, "studentForm": studentForm}
    if request.method == "POST":
        userForm = SFORM.StudentUserForm(request.POST, instance=user)
        studentForm = SFORM.StudentForm(request.POST, request.FILES, instance=student)
        if userForm.is_valid() and studentForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            studentForm.save()
            return redirect("admin-view-student")
    return render(request, "exam/update_student.html", context=mydict)


@login_required(login_url="adminlogin")
def delete_student_view(request, pk):
    student = SMODEL.Student.objects.get(id=pk)
    user = User.objects.get(id=student.user_id)
    involvements = QMODEL.TeacherStudentInvolvement.objects.all().filter(student=student)
    results = QMODEL.Result.objects.all().filter(student=student)
    for i in involvements:
        i.delete()
    for r in results:
        r.delete()
    user.delete()
    student.delete()
    return HttpResponseRedirect("/admin-view-student")


@login_required(login_url="adminlogin")
def admin_course_view(request):
    return render(request, "exam/admin_course.html")


@login_required(login_url="adminlogin")
def admin_add_course_view(request):
    courseForm = forms.CourseForm()
    if request.method == "POST":
        courseForm = forms.CourseForm(request.POST)
        if courseForm.is_valid():
            courseForm.save()
        else:
            print("form is invalid")
        return HttpResponseRedirect("/admin-view-course")
    return render(request, "exam/admin_add_course.html", {"courseForm": courseForm})


@login_required(login_url="adminlogin")
def admin_view_course_view(request):
    courses = models.Course.objects.all()
    return render(request, "exam/admin_view_course.html", {"courses": courses})


@login_required(login_url="adminlogin")
def delete_course_view(request, pk):
    course = models.Course.objects.get(id=pk)
    results = models.Result.objects.all().filter(exam=course)
    questions = models.Question.objects.all().filter(course=course)
    for r in results:
        r.delete()
    for q in questions:
        q.delete()
    course.delete()
    return HttpResponseRedirect("/admin-view-course")


@login_required(login_url="adminlogin")
def admin_question_view(request):
    return render(request, "exam/admin_question.html")


@login_required(login_url="adminlogin")
def admin_add_question_view(request):
    questionForm = forms.QuestionForm()
    if request.method == "POST":
        questionForm = forms.QuestionForm(request.POST)
        if questionForm.is_valid():
            question = questionForm.save(commit=False)
            course = models.Course.objects.get(id=request.POST.get("courseID"))
            question.course = course
            question.save()
        else:
            print("form is invalid")
        return HttpResponseRedirect("/admin-view-question")
    return render(
        request, "exam/admin_add_question.html", {"questionForm": questionForm}
    )


@login_required(login_url="adminlogin")
def admin_view_question_view(request):
    courses = models.Course.objects.all()
    return render(request, "exam/admin_view_question.html", {"courses": courses})


@login_required(login_url="adminlogin")
def view_question_view(request, pk):
    questions = models.Question.objects.all().filter(course_id=pk)
    return render(request, "exam/view_question.html", {"questions": questions})


@login_required(login_url="adminlogin")
def delete_question_view(request, pk):
    question = models.Question.objects.get(id=pk)
    question.delete()
    return HttpResponseRedirect("/admin-view-question")


@login_required(login_url="adminlogin")
def admin_view_marks_view(request, pk):
    courses = models.Course.objects.all()
    response = render(request, "exam/admin_view_marks.html", {"courses": courses})
    response.set_cookie("student_id", str(pk))
    return response


@login_required(login_url="adminlogin")
def admin_check_marks_view(request, pk):
    course = models.Course.objects.get(id=pk)
    student_id = request.COOKIES.get("student_id")
    student = SMODEL.Student.objects.get(id=student_id)

    results = models.Result.objects.all().filter(exam=course).filter(student=student)
    return render(request, "exam/admin_check_marks.html", {"results": results})


def aboutus_view(request):
    return render(request, "exam/aboutus.html")


def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == "POST":
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data["Email"]
            name = sub.cleaned_data["Name"]
            message = sub.cleaned_data["Message"]
            # send_mail(str(name)+' || '+str(email),message,settings.EMAIL_HOST_USER, settings.EMAIL_RECEIVING_USER, fail_silently = True)
            models.ContactUsResponse(email=email, name=name, message=message).save()
            return render(request, "exam/contactussuccess.html")
    return render(request, "exam/contactus.html", {"form": sub})


@login_required(login_url="adminlogin")
def contactus_responses(request):
    dict = {"responses": models.ContactUsResponse.objects.all()}
    return render(request, "exam/admin_contact_us_responses.html", context=dict)
