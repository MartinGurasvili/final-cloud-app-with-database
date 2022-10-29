import sys
from django.utils.timezone import now
try:
    from django.db import models
except Exception:
    print("There was an error loading django modules. Do you have django installed?")
    sys.exit()

from django.conf import settings
import uuid


# Instructor model
class Instructor(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    full_time = models.BooleanField(default=True)
    total_learners = models.IntegerField()

    def __str__(self):
        return self.user.username


# Learner model
class Learner(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    STUDENT = 'student'
    DEVELOPER = 'developer'
    DATA_SCIENTIST = 'data_scientist'
    DATABASE_ADMIN = 'dba'
    OCCUPATION_CHOICES = [
        (STUDENT, 'Student'),
        (DEVELOPER, 'Developer'),
        (DATA_SCIENTIST, 'Data Scientist'),
        (DATABASE_ADMIN, 'Database Admin')
    ]
    occupation = models.CharField(
        null=False,
        max_length=20,
        choices=OCCUPATION_CHOICES,
        default=STUDENT
    )
    social_link = models.URLField(max_length=200)

    def __str__(self):
        return self.user.username + "," + \
               self.occupation


# Course model
class Course(models.Model):
    name = models.CharField(null=False, max_length=30, default='online course')
    image = models.ImageField(upload_to='course_images/')
    description = models.CharField(max_length=1000)
    pub_date = models.DateField(null=True)
    instructors = models.ManyToManyField(Instructor)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, through='Enrollment')
    total_enrollment = models.IntegerField(default=0)
    is_enrolled = False

    def __str__(self):
        return "Name: " + self.name + "," + \
               "Description: " + self.description


# Lesson model
class Lesson(models.Model):
    title = models.CharField(max_length=200, default="title")
    order = models.IntegerField(default=0)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    content = models.TextField()


# Enrollment model
# Once a user enrolled a class, an enrollment entry should be created between the user and course
# And we could use the enrollment to track information such as exam submissions
class Enrollment(models.Model):
    AUDIT = 'audit'
    HONOR = 'honor'
    BETA = 'BETA'
    COURSE_MODES = [
        (AUDIT, 'Audit'),
        (HONOR, 'Honor'),
        (BETA, 'BETA')
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date_enrolled = models.DateField(default=now)
    mode = models.CharField(max_length=5, choices=COURSE_MODES, default=AUDIT)
    rating = models.FloatField(default=5.0)


# Create a Question Model with:
    # Used to persist question content for a course
    # Has a One-To-Many relationship with course. It can be Many-To-Many, but reusing won't be much 
    # common and it could be confusing.
    # Has a grade point for each question
    # Has question text
    # A field for indicating if an answer gives points if partially correct 
class Question(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    text = models.CharField(max_length=200, default="title")
    mark = models.FloatField()
    is_partially_correct_accepted = models.BooleanField()

    # A method to workout question presentation type
    @property
    def get_question_type(self):
        all_correct_answers = self.choice_set.filter(is_correct=True).count()
        if (self.is_partially_correct_accepted == False) and (all_correct_answers == 1):
            return 'radio'
        else:
            return 'checkbox'

    # A  method to calculate the score of the question, giving the mark corresponding 
    # to que anwered question
    def get_score(self, selected_ids):
        all_correct_answers = self.choice_set.filter(is_correct=True).count()
        if (self.is_partially_correct_accepted == False) and (all_correct_answers == 1):
            selected_correct = self.choice_set.filter(is_correct=True, id__in=selected_ids).count()
            if all_correct_answers == selected_correct:
                return self.mark
            else:
                return 0
        else:
            total_answers = 0
            correct_answers = 0
            for choice in self.choice_set.all():
                total_answers += 1
                if ((choice.id in selected_ids) and (choice.is_correct)) or \
                        ((choice.id not in selected_ids) and (not choice.is_correct)):  
                    correct_answers += 1
            return self.mark*correct_answers/total_answers

#  Create a Choice Model with:
    # Used to persist choice content for a question
    # One-To-Many relationship with Question. It can be Many-To-Many, but reusing won't be much 
    # common and it could be confusing.
    # Choice content
    # Indicate if this choice of the question is a correct one or not
class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=200, default="title")
    is_correct = models.BooleanField()


# The submission model
# One enrollment could have multiple submission
# One submission could have multiple choices
# One choice could belong to multiple submissions
class Submission(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    choices = models.ManyToManyField(Choice)