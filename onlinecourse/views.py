from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import View, generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
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
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def get_enrollement(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        results = Enrollment.objects.filter(user=user, course=course)
        if results.count() > 0:
            return results.first()
    return None


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = (get_enrollement(user, course) != None)
        return courses

# CourseDetailView
class CourseDetailView(View):

    def get(self, request, *args, **kwargs):
        try:
            context = {}
            course_id = kwargs.get('pk')
            user = self.request.user
            course = Course.objects.get(pk=course_id)
            enrollment = get_enrollement(user, course)
            if user.is_authenticated:
                course.is_enrolled = (enrollment != None)
            course.best_grade = -1
            for submission in enrollment.submission_set.all():
                exam_mark = 0.0
                highest_mark_possible = 0.0
                for question in course.question_set.all():
                    chosen_answers_ids = list(map(lambda x: x.id, submission.choices \
                            .filter(question__id=question.id).all()))
                    question.mark_resolved = question.get_score(chosen_answers_ids)
                    exam_mark += question.mark_resolved
                    highest_mark_possible += question.mark
                if (highest_mark_possible > 0) and (exam_mark <= highest_mark_possible):
                    grade = int(exam_mark / highest_mark_possible * 100)   
                    if (grade > course.best_grade):
                        course.best_grade = grade
            context['course'] = course
            return render(request, 'onlinecourse/course_detail_bootstrap.html', context)
        except Course.DoesNotExist:
            raise Http404("No course matches the given id.")

def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    
    action = request.POST['action']

    if action == "Cancel enrollement": 
        enrollement = get_enrollement(user, course)
        if (enrollement != None) and user.is_authenticated:
            # Delete enrollment
            enrollement.delete()
            course.total_enrollment -= 1
            course.save()
        return HttpResponseRedirect(reverse(viewname='onlinecourse:index'))    
    elif action == "Enroll": 
        enrollement = get_enrollement(user, course)
        if (enrollement == None) and user.is_authenticated:
            # Create an enrollment
            Enrollment.objects.create(user=user, course=course, mode='honor')
            course.total_enrollment += 1
            course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# Submit view to create an exam submission record for a course enrollment,
# Implementation based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollment
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Save submission object in the database
         # Redirect to show_exam_result with the submission id
def submit(request, course_id):
    user = request.user
    if not user.is_authenticated:
        return HttpResponseNotFound("User is not authenticated")  
    course = get_object_or_404(Course, pk=course_id)
    enrollment = get_enrollement(user, course)
    if enrollment is None:
        return HttpResponseNotFound("User is not enrolled to course")  
    submission = Submission.objects.create(enrollment=enrollment)
    selected_choices = extract_answers(request)
    submission.choices.set(selected_choices)
    submission.save()
    return HttpResponseRedirect(reverse(viewname='onlinecourse:show_exam_result', args=(course.id, submission.id,)))


# Method to collect the selected choices from the exam form from the request object
def extract_answers(request):
    submitted_anwsers = []
    for key in request.POST:
        if key.startswith('choice') or key.startswith('question'):
            value = request.POST[key]
            choice_id = int(value)
            submitted_anwsers.append(choice_id)
    return submitted_anwsers


# Exam result view to check if learner passed exam and show their question results and result for each question,
# Implementation based on the following logic:
        # Get logged user, course and submission based on their ids
        # Initiate two counters, one for the mark got and other for the hightest one possible
        # Get the selected choice ids from the submission record
        # For each question, get the choices given to the question and get the mark of the question
        #       with them. Save the info about the choices selected (if ok or not and similar).
        # Update the exam mark and the highest mark possible.
        # Calculate the total score as percentage of mark got, and save it as part of the course object.
        # Redirect to the exam results template, passing the completed course and questions objects in the context.
def show_exam_result(request, course_id, submission_id):
    user = request.user
    if not user.is_authenticated:
        return HttpResponseNotFound("User is not authenticated")  
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)
    exam_mark = 0.0
    highest_mark_possible = 0.0
    questions = course.question_set.all()
    for question in questions:
        chosen_answers_ids = list(map(lambda x: x.id, submission.choices \
        		.filter(question__id=question.id).all()))
        question.mark_resolved = question.get_score(chosen_answers_ids)
        exam_mark += question.mark_resolved
        highest_mark_possible += question.mark
        if question.mark_resolved == question.mark:
            question.result = "success"
        elif question.mark_resolved == 0:
            question.result = "failed"
        else:
            question.result = "partial"
        question.choices = question.choice_set.all()
        for choice in question.choices:
            if choice.id in chosen_answers_ids:
                choice.is_selected = True
                if choice.is_correct:
                    choice.is_resolved_correctly = True
                else:
                    choice.is_resolved_correctly = False
            else:
                choice.is_selected = False
                if choice.is_correct:
                    choice.is_resolved_correctly = False
                else:
                    choice.is_resolved_correctly = True 
    if (highest_mark_possible <= 0) or (exam_mark > highest_mark_possible):
        return HttpResponseNotFound("Rerror resolving exam")
    else:
        course.grade = int(exam_mark / highest_mark_possible * 100)   
        context = {}
        context['course'] = course
        context['questions'] = questions
        return render(request, 'onlinecourse/exam_result_bootstrap.html', context)  




