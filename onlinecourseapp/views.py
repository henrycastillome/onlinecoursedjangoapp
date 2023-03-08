from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)



def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourseapp/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourseapp:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourseapp/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourseapp:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourseapp/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourseapp/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourseapp:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(
            user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourseapp/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourseapp/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourseapp:course_details', args=(course.id,)))




def submit(request, course_id):
    user = request.user
    course = get_object_or_404(Course, pk=course_id)

    enrollment = Enrollment.objects.get(user=user, course=course)
    submission = Submission(enrollment=enrollment)

    selected_choices = []
    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST[key]
            choice_id = int(value)
            selected_choices.append(choice_id)

    submission.save()

    for choice_id in selected_choices:
        choice = Choice.objects.get(pk=choice_id)
        submission.choices.add(choice)

    return HttpResponseRedirect(reverse('onlinecourseapp:show_exam_result', args=(course_id, submission.id,)))


def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)
    selected_choices = submission.choices.all()

    score = 0
    total_marks = 0

    # iterate through each choice in selected_choices, adding the grade of the corresponding question to
    # total_marks and to score if the choice is a correct answer.

    for choice in selected_choices:
        total_marks += choice.question.grade
        if choice.is_correct:
            score += choice.question.grade

    # It first evaluates the expression total_marks, if it is True then it returns the value of total_marks, otherwise it returns 0.
    percentage = round((score / total_marks) * 100) if total_marks else 0

    if percentage >= 80:
        message = 'passed'
    else:
        message = 'failed'

    context = {'course': course, 'score': score, 'total_marks': total_marks, 'percentage': percentage, 'message': message,
               'selected_choices': selected_choices}

    return render(request, 'onlinecourseap/exam_result_bootstrap.html', context)
