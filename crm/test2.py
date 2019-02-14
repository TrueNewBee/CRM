# by luffycity.com

from stark.service.stark import site, ModelStark

from .models import *

site.register(School)


class UserConfig(ModelStark):
    list_display = ["name", "email", "depart"]


site.register(UserInfo, UserConfig)


class ClassConfig(ModelStark):
    def display_classname(self, obj=None, header=False):
        if header:
            return "班级名称"
        class_name = "%s(%s)" % (obj.course.name, str(obj.semester))
        return class_name

    list_display = [display_classname, "tutor", "teachers"]


site.register(ClassList, ClassConfig)

from django.utils.safestring import mark_safe
from django.conf.urls import url

from django.shortcuts import HttpResponse, redirect, render


class CusotmerConfig(ModelStark):
    def display_gender(self, obj=None, header=False):
        if header:
            return "性别"
        return obj.get_gender_display()

    def display_course(self, obj=None, header=False):
        if header:
            return "咨询课程"
        temp = []
        for course in obj.course.all():
            s = "<a href='/stark/crm/customer/cancel_course/%s/%s' style='border:1px solid #369;padding:3px 6px'><span>%s</span></a>&nbsp;" % (
                obj.pk, course.pk, course.name,)
            temp.append(s)
        return mark_safe("".join(temp))

    list_display = ["name", display_gender, display_course, "consultant", ]

    def cancel_course(self, request, customer_id, course_id):
        print(customer_id, course_id)

        obj = Customer.objects.filter(pk=customer_id).first()
        obj.course.remove(course_id)
        return redirect(self.get_list_url())

    def public_customer(self, request):

        # 未报名 且3天未跟进或者15天未成单

        from django.db.models import Q
        import datetime
        now = datetime.datetime.now()

        '''
        datetime.datetime
        datetime.time
        datetime.date
        datetime.timedelta(days=7)

        '''
        # 三天未跟进 now-last_consult_date>3   --->last_consult_date<now-3
        # 15天未成单 now-recv_date>15   --->recv_date<now-15

        delta_day3 = datetime.timedelta(days=3)
        delta_day15 = datetime.timedelta(days=15)
        user_id = 5
        customer_list = Customer.objects.filter(
            Q(last_consult_date__lt=now - delta_day3) | Q(recv_date__lt=now - delta_day15), status=2).exclude(
            consultant=user_id)
        print(customer_list)
        return render(request, "public.html", locals())

    def further(self, request, customer_id):

        user_id = 3  # request.session.get("user_id")
        import datetime

        now = datetime.datetime.now()
        delta_day3 = datetime.timedelta(days=3)
        delta_day15 = datetime.timedelta(days=15)
        from django.db.models import Q

        # 为改客户更改课程顾问，和对应时间
        ret = Customer.objects.filter(pk=customer_id).filter(
            Q(last_consult_date__lt=now - delta_day3) | Q(recv_date__lt=now - delta_day15), status=2).update(
            consultant=user_id, last_consult_date=now, recv_date=now)
        if not ret:
            return HttpResponse("已经被跟进了")

        CustomerDistrbute.objects.create(customer_id=customer_id, consultant_id=user_id, date=now, status=1)

        return HttpResponse("跟进成功")

    def mycustomer(self, request):
        user_id = 2
        customer_distrbute_list = CustomerDistrbute.objects.filter(consultant=user_id)

        return render(request, "mycustomer.html", locals())

    def extra_url(self):

        temp = []

        temp.append(url(r"cancel_course/(\d+)/(\d+)", self.cancel_course))
        temp.append(url(r"public/", self.public_customer))
        temp.append(url(r"further/(\d+)", self.further))
        temp.append(url(r"mycustomer/", self.mycustomer))

        return temp


site.register(Customer, CusotmerConfig)
site.register(Department)
site.register(Course)


class ConsultConfig(ModelStark):
    list_display = ["customer", "consultant", "date", "note"]


site.register(ConsultRecord, ConsultConfig)

from django.http import JsonResponse


class StudentConfig(ModelStark):
    def score_view(self, request, sid):
        if request.is_ajax():

            print(request.GET)

            sid = request.GET.get("sid")
            cid = request.GET.get("cid")

            study_record_list = StudyRecord.objects.filter(student=sid, course_record__class_obj=cid)

            data_list = []

            for study_record in study_record_list:
                day_num = study_record.course_record.day_num
                data_list.append(["day%s" % day_num, study_record.score])
            print(data_list)
            return JsonResponse(data_list, safe=False)


        else:
            student = Student.objects.filter(pk=sid).first()
            class_list = student.class_list.all()

            return render(request, "score_view.html", locals())

    def extra_url(self):
        temp = []
        temp.append(url(r"score_view/(\d+)", self.score_view))
        return temp

    def score_show(self, obj=None, header=False):
        if header:
            return "查看成绩"
        return mark_safe("<a href='/stark/crm/student/score_view/%s'>查看成绩</a>" % obj.pk)

    list_display = ["customer", "class_list", score_show]
    list_display_links = ["customer"]


site.register(Student, StudentConfig)


class CourseRecordConfig(ModelStark):
    def score(self, request, course_record_id):
        if request.method == "POST":
            print(request.POST)

            data = {}
            for key, value in request.POST.items():

                if key == "csrfmiddlewaretoken": continue

                field, pk = key.rsplit("_", 1)

                if pk in data:
                    data[pk][field] = value
                else:
                    data[pk] = {field: value}  # data  {4:{"score":90}}

            print("data", data)

            for pk, update_data in data.items():
                StudyRecord.objects.filter(pk=pk).update(**update_data)

            return redirect(request.path)


        else:
            study_record_list = StudyRecord.objects.filter(course_record=course_record_id)
            score_choices = StudyRecord.score_choices
            return render(request, "score.html", locals())

    def extra_url(self):

        temp = []
        temp.append(url(r"record_score/(\d+)", self.score))
        return temp

    def record(self, obj=None, header=False):
        if header:
            return "学习记录"
        return mark_safe("<a href='/stark/crm/studyrecord/?course_record=%s'>记录</a>" % obj.pk)

    def record_score(self, obj=None, header=False):
        if header:
            return "录入成绩"
        return mark_safe("<a href='record_score/%s'>录入成绩</a>" % obj.pk)

    list_display = ["class_obj", "day_num", "teacher", record, record_score]

    def patch_studyrecord(self, request, queryset):
        print(queryset)
        temp = []
        for course_record in queryset:
            # 与course_record关联的班级对应所有学生
            student_list = Student.objects.filter(class_list__id=course_record.class_obj.pk)
            for student in student_list:
                obj = StudyRecord(student=student, course_record=course_record)
                temp.append(obj)
        StudyRecord.objects.bulk_create(temp)

    patch_studyrecord.short_description = "批量生成学习记录"
    actions = [patch_studyrecord, ]


site.register(CourseRecord, CourseRecordConfig)


class StudyConfig(ModelStark):
    list_display = ["student", "course_record", "record", "score"]

    def patch_late(self, request, queryset):
        queryset.update(record="late")

    patch_late.short_description = "迟到"
    actions = [patch_late]


site.register(StudyRecord, StudyConfig)
site.register(CustomerDistrbute)
