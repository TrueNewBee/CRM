from stark.service.stark import site, ModelStark
from django.utils.safestring import mark_safe
from django.conf.urls import url
from django.shortcuts import redirect, render, HttpResponse
from .models import *
from django.http import JsonResponse
from django.db.models import Q
import datetime

"""
可以配置字段:
        1. list_display[]   可以添加自定义展示字段,也可以添加函数名
        2. 父类提供的添加该表额外url的接口 def extra_url  重写这个方法即可
2018-10-22 21:33:33
增加部分:
        1. 初始化  course_record,studyrecord,
        2. 考勤
        3. 录入成绩
2018-10-23 20:21:35
增加功能:
        1.通过Ajax,调用highchats插件,把学员个人成绩做成柱状图
        2.增添了公共客户展示,并且可以选择跟进
        3.	---公共客户(公共资源)
               1 没有报名
               2 3天没有跟进
               3 15天没有成单
            ps 关于这个条件,可以用linux做一个定时器,定时执行一下脚本,检查符合上述条件的客户进行修改更新信息,
                这个理解就好!不做重点!
为了方便,把目前的配置类的各种可访问接口总结一下:
    customer/public/            访问公共资源
    customer/mycustomer/        访问我的个人客户页面

"""


# 用户配置表
class UserConfig(ModelStark):
    # 自定义展示字段 list_display[]
    list_display = ["name", "email", "depart"]


# 班级配置表
class ClassConfig(ModelStark):
    # 自定义一个展示函数,然后添加到list_display中
    def display_classname(self, obj=None, header=False):
        if header:
            return "班级名称"
        class_name = "%s(%s)" % (obj.course.name, str(obj.semester))
        return class_name

    list_display = [display_classname, "tutor", "teachers"]


# 客户配置表
class CustomerConfig(ModelStark):
    # 自定义展示性别
    def display_gender(self, obj=None, header=False):
        if header:
            return "性别"
        return obj.get_gender_display()

    # 自定义展示课程
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

    # 取消课程的视图函数
    def cancel_course(self, request, customer_id, course_id):
        print(customer_id, course_id)
        obj = Customer.objects.filter(pk=customer_id).first()
        obj.course.remove(course_id)
        return redirect(self.get_list_url())

    # 展示公共客户的视图函数
    def public_customer(self, request):
        # 未报名 且3天未跟进或者15天未成单
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
        # 筛选出符合条件的客户,并且不是该登录者跟进的客户
        customer_list = Customer.objects.filter(
            Q(last_consult_date__lt=now - delta_day3) | Q(recv_date__lt=now - delta_day15), status=2).exclude(
            consultant=user_id)
        print(customer_list)
        return render(request, "public.html", locals())

    # 选择跟进用户的视图函数
    def further(self, request, customer_id):
        # 由于没有加入rbac权限管理系统,先写死用户id  加入rbac后可用: request.session.get("user_id")
        user_id = 3     # alex
        now = datetime.datetime.now()
        delta_day3 = datetime.timedelta(days=3)
        delta_day15 = datetime.timedelta(days=15)
        # 为改客户更改课程顾问，和对应时间
        ret = Customer.objects.filter(pk=customer_id).filter(
            Q(last_consult_date__lt=now - delta_day3) | Q(recv_date__lt=now - delta_day15), status=2).update(
            consultant=user_id, last_consult_date=now, recv_date=now)
        if not ret:
            return HttpResponse("已经被跟进了")
        # 在客户跟进表中添加一条新的记录
        CustomerDistrbute.objects.create(customer_id=customer_id, consultant_id=user_id, date=now, status=1)
        return HttpResponse("跟进成功")

    # 展示我的客户的视图函数
    def mycustomer(self, request):
        # 由于没有加入rbac权限管理系统,先写死用户id  加入rbac后可用: request.session.get("user_id")
        user_id = 3         # alex
        # 在客户跟进表中通过user_id 拿到该用户名下所有的客户跟进记录
        customer_distrbute_list = CustomerDistrbute.objects.filter(consultant=user_id)
        return render(request, "mycustomer.html", locals())

    # 父类给出的添加额外url的接口
    def extra_url(self):
        temp = []
        temp.append(url(r"cancel_course/(\d+)/(\d+)", self.cancel_course))
        temp.append(url(r"public/", self.public_customer))
        temp.append(url(r"further/(\d+)", self.further))
        temp.append(url(r"mycustomer/", self.mycustomer))
        return temp


# 咨询配置表
class ConsultConfig(ModelStark):
    # 自定义展示字段
    list_display = ["customer", "consultant", "date", "note"]


# 学生配置表
class StudentConfig(ModelStark):
    # 查看成绩
    def score_view(self,request,sid):
        if request.is_ajax():
            print(request.GET)
            sid=request.GET.get("sid")
            cid=request.GET.get("cid")
            study_record_list=StudyRecord.objects.filter(student=sid,course_record__class_obj=cid)
            data_list=[]
            for study_record in study_record_list:
                day_num=study_record.course_record.day_num
                data_list.append(["day%s"%day_num,study_record.score])
            print(data_list)
            return JsonResponse(data_list,safe=False)
        else:
            student=Student.objects.filter(pk=sid).first()
            class_list=student.class_list.all()
            return render(request,"score_view.html",locals())

    def extra_url(self):
        temp = []
        temp.append(url(r"score_view/(\d+)", self.score_view))
        return temp

    def score_show(self, obj=None, header=False):
        if header:
            return "查看成绩"
        return mark_safe("<a href='/stark/crm/student/score_view/%s'>查看成绩</a>"%obj.pk)

    list_display = ["customer", "class_list",score_show]
    list_display_links = ["customer"]


# 学习情况配置表
class StudyConfig(ModelStark):
    # 自定义展示字段
    list_display = ["student", "course_record", "record", "score"]

    def patch_late(self, request, queryset):
        queryset.update(record="late")

    # 批量更改为 迟到
    patch_late.short_description = "一键迟到"
    actions = [patch_late]


# 课程记录配置表
class CourseRecordConfig(ModelStark):
    # 记录成绩的视图函数
    def score(self, request, course_record_id):
        if request.method == "POST":
            print(request.POST)
            data = {}
            for key, value in request.POST.items():
                if key == "csrfmiddlewaretoken": continue
                print("key:", key)           # key: score_1
                # 取到键值pk 后面数字
                field, pk = key.rsplit("_", 1)
                if pk in data:
                    data[pk][field] = value
                else:
                    data[pk] = {field: value}  # data  {4:{"score":90}}
            print("data", data)
            # 构建成如下的数据 虽然构建数据有些麻烦,但是节省了储存数据库所需时间
            # data {'1': {'score': '100', 'homework_note': '11'}, '2': {'score': '85', 'homework_note': '22'}}
            for pk, update_data in data.items():
                StudyRecord.objects.filter(pk=pk).update(**update_data)
            return redirect(request.path)
        else:
            # 把数据传入前端,然后渲染列表数据
            study_record_list = StudyRecord.objects.filter(course_record=course_record_id)
            score_choices = StudyRecord.score_choices
            return render(request, "score.html", locals())

    # 通过内置接口 分发一个记录成绩的url
    def extra_url(self):
        temp = []
        temp.append(url(r"record_score/(\d+)", self.score))
        return temp

    # 定义考勤的函数
    def record(self, obj=None, header=False):
        if header:
            return "考勤"
        return mark_safe("<a href='/stark/crm/studyrecord/?course_record=%s'>记录</a>" % obj.pk)

    # 定义录入成绩的函数
    def record_score(self, obj=None, header=False):
        if header:
            return "录入成绩"
        return mark_safe("<a href='record_score/%s'>录入成绩</a>" % obj.pk)

    list_display = ["class_obj", "day_num", "teacher", record, record_score]

    # 批量添加学生学习记录
    def patch_studyrecord(self, request, queryset):
        print(queryset)
        temp = []
        for course_record in queryset:
            # 与course_record关联的班级对应所有学生
            student_list = Student.objects.filter(class_list__id=course_record.class_obj.pk)
            for student in student_list:
                obj = StudyRecord(student=student, course_record=course_record)
                temp.append(obj)
        # 在StudyRecord表中批量添加学生学习记录
        StudyRecord.objects.bulk_create(temp)
    patch_studyrecord.short_description = "批量生成学习记录"
    actions = [patch_studyrecord, ]


site.register(UserInfo, UserConfig)
site.register(Customer, CustomerConfig)
site.register(Student, StudentConfig)
site.register(ConsultRecord, ConsultConfig)
site.register(StudyRecord, StudyConfig)
site.register(CourseRecord, CourseRecordConfig)
site.register(ClassList, ClassConfig)
site.register(School)
site.register(Department)
site.register(Course)
site.register(CustomerDistrbute)
