from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.db.models import Sum
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required,user_passes_test
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa
from exam import models as QMODEL
from student import models as SMODEL
from exam import forms as QFORM


#for showing signup/login button for teacher
def teacherclick_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')
    return render(request,'teacher/teacherclick.html')

def teacher_signup_view(request):
    userForm=forms.TeacherUserForm()
    teacherForm=forms.TeacherForm()
    mydict={'userForm':userForm,'teacherForm':teacherForm}
    if request.method=='POST':
        userForm=forms.TeacherUserForm(request.POST)
        teacherForm=forms.TeacherForm(request.POST,request.FILES)
        if userForm.is_valid() and teacherForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            teacher=teacherForm.save(commit=False)
            teacher.user=user
            teacher.save()
            my_teacher_group = Group.objects.get_or_create(name='TEACHER')
            my_teacher_group[0].user_set.add(user)
        return HttpResponseRedirect('teacherlogin')
    return render(request,'teacher/teachersignup.html',context=mydict)



def is_teacher(user):
    return user.groups.filter(name='TEACHER').exists()

@login_required(login_url='teacherlogin')
@user_passes_test(is_teacher)
def teacher_dashboard_view(request):
    dict={
    
    'total_course':QMODEL.Course.objects.all().count(),
    'total_question':QMODEL.Question.objects.all().count(),
    'total_student':SMODEL.Student.objects.all().count()
    }
    return render(request,'teacher/teacher_dashboard.html',context=dict)

@login_required(login_url='teacherlogin')
@user_passes_test(is_teacher)
def teacher_exam_view(request):
    return render(request,'teacher/teacher_exam.html')


@login_required(login_url='teacherlogin')
@user_passes_test(is_teacher)
def teacher_add_exam_view(request):
    courseForm=QFORM.CourseForm()
    if request.method=='POST':
        try:
            cname = request.POST.get('course_name')
            qcount = int(request.POST.get('question_number'))
            totalMarks = int(request.POST.get('total_marks'))
            teacher = models.Teacher.objects.all().filter(user=models.User.objects.all().filter(id=request.user.id).first()).first()
            if cname.strip()=='' or totalMarks <= 0 or qcount <= 0:
                raise Exception
        except:
            print('Invalid Form')
        course = QMODEL.Course(
            course_name = cname,
            question_number = qcount,
            total_marks = totalMarks,
            teacher = teacher
        )
        course.save()
        for i in range(qcount):
            QMODEL.Question(
                course=course,
                marks = 0,
                question = "",
                option1 = "",
                option2 = "",
                option3 = "",
                option4 = "",
                answer = "option1"
            ).save()
        return HttpResponseRedirect('/teacher/teacher-view-exam')
    return render(request,'teacher/teacher_add_exam.html',{'courseForm':courseForm})

@login_required(login_url='teacherlogin')
@user_passes_test(is_teacher)
def teacher_view_exam_view(request):
    teacher = models.Teacher.objects.all().filter(user=models.User.objects.all().filter(id=request.user.id).first()).first()
    courses = QMODEL.Course.objects.all().filter(teacher=teacher)
    return render(request,'teacher/teacher_view_exam.html',{'courses':courses})

@login_required(login_url='teacherlogin')
@user_passes_test(is_teacher)
def teacher_download_exam_report(request, eID):
    course = QMODEL.Course.objects.all().filter(id = eID).first()
    results = QMODEL.Result.objects.all().filter(exam = eID).all()

    template = get_template('teacher/teacher_exam_report.html')
    html = template.render({'course': course, 'results': results, 'totalMarks': sum([r.marks for r in results]), "resultCount": len(results), "average": sum([r.marks for r in results])/(lambda x: x if x else 1)(len(results))})
    response = HttpResponse(content_type='application/pdf')
    pdf_status = pisa.CreatePDF(html, dest=response)

    if pdf_status.err:
        return HttpResponse('Some errors were encountered <pre>' + html + '</pre>')
    return response

@login_required(login_url='teacherlogin')
@user_passes_test(is_teacher)
def delete_exam_view(request,pk):
    course=QMODEL.Course.objects.get(id=pk)
    course.delete()
    return HttpResponseRedirect('/teacher/teacher-view-exam')

@login_required(login_url='adminlogin')
def teacher_question_view(request):
    return render(request,'teacher/teacher_question.html')

@login_required(login_url='teacherlogin')
@user_passes_test(is_teacher)
def teacher_add_question_view(request, courseID):
    if request.method=='POST':
        course=QMODEL.Course.objects.get(id=courseID)
        questions=QMODEL.Question.objects.all().filter(course=course)
        for question in questions:
            qtext=request.POST.get(f'question-{question.id}')
            mark=request.POST.get(f'mark-{question.id}')
            opt1=request.POST.get(f'opt1-{question.id}')
            opt2=request.POST.get(f'opt2-{question.id}')
            opt3=request.POST.get(f'opt3-{question.id}')
            opt4=request.POST.get(f'opt4-{question.id}')
            answer=request.POST.get(f'answer-{question.id}')
            question.question=qtext
            question.marks=mark
            question.option1=opt1
            question.option2=opt2
            question.option3=opt3
            question.option4=opt4
            question.answer=answer
            question.save()
        return HttpResponseRedirect(f'/teacher/teacher-exam')
    teacher = models.Teacher.objects.all().filter(user=models.User.objects.all().filter(id=request.user.id).first()).first()
    course = QMODEL.Course.objects.get(id=courseID)
    questions = QMODEL.Question.objects.all().filter(course=course).all()
    return render(request,'teacher/teacher_add_question.html',{'questions': questions, 'course':course, 'teacher':teacher})

@login_required(login_url='teacherlogin')
@user_passes_test(is_teacher)
def teacher_view_question_view(request):
    teacher = models.Teacher.objects.all().filter(user=models.User.objects.all().filter(id=request.user.id).first()).first()
    courses= QMODEL.Course.objects.all().filter(teacher=teacher)
    return render(request,'teacher/teacher_view_question.html',{'courses':courses})

@login_required(login_url='teacherlogin')
@user_passes_test(is_teacher)
def see_question_view(request,pk):
    questions=QMODEL.Question.objects.all().filter(course_id=pk)
    return render(request,'teacher/see_question.html',{'questions':questions})

@login_required(login_url='teacherlogin')
@user_passes_test(is_teacher)
def remove_question_view(request,pk):
    question=QMODEL.Question.objects.get(id=pk)
    question.delete()
    return HttpResponseRedirect('/teacher/teacher-view-question')

@login_required(login_url='teacherlogin')
def teacher_student_view(request):
    teacher = models.Teacher.objects.all().filter(user=models.User.objects.all().filter(id=request.user.id).first()).first()
    dict={
        'total_student': QMODEL.TeacherStudentInvolvement.objects.all().filter(teacher=teacher).count(),
    }
    return render(request,'exam/admin_student.html',context=dict)

@login_required(login_url='adminlogin')
def view_student_view(request):
    teacher = models.Teacher.objects.all().filter(user=models.User.objects.all().filter(id=request.user.id).first()).first()
    students= QMODEL.TeacherStudentInvolvement.objects.all().filter(teacher=teacher)
    return render(request,'exam/teacher_view_student.html',{'students':students})

@login_required(login_url='adminlogin')
def allow_student(request, involvementID):
    involvement = QMODEL.TeacherStudentInvolvement.objects.all().filter(id=involvementID).first()
    involvement.allowed = True
    involvement.save()
    return redirect('view-students')

@login_required(login_url='adminlogin')
def view_student_marks_view(request):
    students= SMODEL.Student.objects.all()
    return render(request,'exam/admin_view_student_marks.html',{'students':students})