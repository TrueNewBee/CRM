from django.conf.urls import url
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db.models import Q
from django.utils.safestring import mark_safe
from stark.utils.page import Pagination
from django.db.models.fields.related import ForeignKey
from django.db.models.fields.related import ManyToManyField
from django.forms import ModelForm
import copy

"""
Stark组件!
2018-10-21 20:21:41
功能简介:
        由于原来做的stark有bug,所以修改了一下,setting注册就可以使用完美仿照admin
        *********
        1. 使用方法和Django的admin一样,需要在stark里面注册,详情看app01/stark.py
        2. 实现了对不同表的url的各级分发
        3. 用户可以自定义配置表的现实信息 详情可以看app01/stark.py
        4. 实现了对表添加数据pop的功能!
        5. 最强大就是,你可以拿去直接用,和admin一样,而且不需要超级用户!
        2333333333333333333333333333333
"""


# List视图用于解耦的一个类
class ShowList(object):
    # 这是一个配置类的对象初始化
    def __init__(self, config, data_list, request):
        self.config = config
        self.data_list = data_list
        self.request = request
        # 分页
        data_count = self.data_list.count()
        current_page = int(self.request.GET.get("page", 1))
        base_path = self.request.path
        self.pagination = Pagination(current_page, data_count, base_path, self.request.GET, per_page_num=10,
                                     pager_count=11,)
        self.page_data = self.data_list[self.pagination.start:self.pagination.end]
        # actions   获取actions这个配置类的列表
        self.actions = self.config.new_actions()  # [patch_init,]

    # 处理filter字段连接
    def get_filter_linktags(self):
        """用了两次for循环,在算法上有点缀余!不过可以用类或函数封装只是懒-.-能力欠缺!"""
        print("list_filter:", self.config.list_filter)
        link_dic = {}

        for filter_field in self.config.list_filter:  # ["title","publish","authors",]
            params = copy.deepcopy(self.request.GET)
            cid = self.request.GET.get(filter_field, 0)
            print("filter_field", filter_field)  # "publish"
            # 通过_meta.get_field方法,获取该表名对象
            filter_field_obj = self.config.model._meta.get_field(filter_field)

            # 判断一下 如果是多对多或一对多类型的
            if isinstance(filter_field_obj, ForeignKey) or isinstance(filter_field_obj, ManyToManyField):
                # 拿到表的所有QuerySet对象
                data_list = filter_field_obj.rel.to.objects.all()  # 【publish1,publish2...】
            else:
                # 这个则是自定义过滤字段
                data_list = self.config.model.objects.all().values("pk", filter_field)
                print("data_list", data_list)
            temp = []
            # 处理 全部标签
            if params.get(filter_field):
                # 如果url如果存在参数 则del
                del params[filter_field]
                temp.append("<a href='?%s'>全部</a>" % params.urlencode())
            else:
                # 反之加上class 增加颜色
                temp.append("<a  class='active' href='#'>全部</a>")

            # 处理 数据标签
            for obj in data_list:
                # 循环列表中每个QuerySet的对象然后取到相应的值
                if isinstance(filter_field_obj, ForeignKey) or isinstance(filter_field_obj, ManyToManyField):
                    pk = obj.pk
                    text = str(obj)
                    params[filter_field] = pk
                else:  # data_list= [{"pk":1,"title":"go"},....]
                    pk = obj.get("pk")
                    text = obj.get(filter_field)
                    params[filter_field] = text

                _url = params.urlencode()
                if cid == str(pk) or cid == text:
                    link_tag = "<a class='active' href='?%s'>%s</a>" % (_url, text)
                else:
                    link_tag = "<a href='?%s'>%s</a>" % (_url, text)

                temp.append(link_tag)
            link_dic[filter_field] = temp
        return link_dic

    # 获取下拉框 用户配置的action_list
    def get_action_list(self):
        temp = []
        for action in self.actions:
            # [{"name":""patch_init,"desc":"批量初始化"}]
            temp.append({
                "name": action.__name__,
                "desc": action.short_description
            })
        return temp

    # 构建表头
    def get_header(self):
        # 构建表头
        header_list = []
        print("header", self.config.new_list_play())
        # [checkbox,"pk","name","age",edit ,deletes]     【checkbox ,"__str__", edit ,deletes】

        for field in self.config.new_list_play():
            if callable(field):
                # header_list.append(field.__name__)
                val = field(self.config, header=True)
                header_list.append(val)
            else:
                if field == "__str__":
                    header_list.append(self.config.model._meta.model_name.upper())
                else:
                    # header_list.append(field)
                    val = self.config.model._meta.get_field(field).verbose_name
                    header_list.append(val)
        return header_list

    # 构建表单数据
    def get_body(self):
        # 构建表单数据
        new_data_list = []
        for obj in self.page_data:
            temp = []
            # 切记不可把循环对象命名一样!!容易出bug而且找不到
            for filed in self.config.new_list_play():  # ["__str__",]      ["pk","name","age",edit]
                if callable(filed):
                    print("obj-----:", obj)
                    val = filed(self.config, obj)
                else:
                    # 这里捕获一下异常,因为默认的list_play里面有__str__ 直接找不到该字段
                    # 所以直接用getattr方法就行啦!
                    try:
                        field_obj = self.config.model._meta.get_field(filed)
                        if isinstance(field_obj, ManyToManyField):
                            # getattr()仅取到Object, 然后.all() 则可以取到对象
                            ret = getattr(obj, filed).all()
                            t = []
                            for mobj in ret:
                                t.append(str(mobj))
                            val = ",".join(t)
                        else:
                            # 判断是否含有choices字段,就是多选元组(1, 男)这样的
                            if field_obj.choices:
                                # 如果有则反射  get_fueld_display 方法 取到后面的值 这个方法不用在配置类自定义啦
                                # 直接写到父类中,默认,在配置类直接写字段就行啦
                                val = getattr(obj, "get_"+filed+"_display")
                            else:
                                 val = getattr(obj, filed)
                            if filed in self.config.list_display_links:
                                # "app01/userinfo/(\d+)/change"
                                _url = self.config.get_change_url(obj)
                                val = mark_safe("<a href='%s'>%s</a>" % (_url, val))
                    except Exception as e:
                        val = getattr(obj, filed)
                temp.append(val)
            new_data_list.append(temp)
        return new_data_list


'''
        [
            [1,"alex",12],
            [1,"alex",12],
            [1,"alex",12],
            [1,"alex",12],

                 ]

 '''


class ModelStark(object):
    list_display = ["__str__", ]
    list_display_links = []
    modelform_class = None
    search_fields = []
    actions = []
    list_filter = []

    def __init__(self, model, site):
        self.model = model
        self.site = site

    # 默认的批量删除action
    def patch_delete(self, request, queryset):
        queryset.delete()
    patch_delete.short_description = "批量删除"

    # 配置表头: 删除 编辑，复选框
    def edit(self, obj=None, header=False):
        """编辑"""
        if header:
            return "操作"
        # return mark_safe("<a href='%s/change'>编辑</a>"%obj.pk)
        _url = self.get_change_url(obj)
        return mark_safe("<a href='%s'>编辑</a>" % _url)

    def deletes(self, obj=None, header=False):
        """删除"""
        if header:
            return "操作"
        # return mark_safe("<a href='%s/change'>编辑</a>"%obj.pk)

        _url = self.get_delete_url(obj)

        return mark_safe("<a href='%s'>删除</a>" % _url)

    def checkbox(self, obj=None, header=False):
        """复选框"""
        if header:
            return mark_safe('<input id="choice" type="checkbox">')
        # value的值不能写死,
        return mark_safe('<input class="choice_item" type="checkbox" name="selected_pk" value="%s">' % obj.pk)

    # 获取配置类的表头信息
    def get_modelform_class(self):
        """获取表的配置类"""
        if not self.modelform_class:
            # 如果表的配置类为空
            class ModelFormDemo(ModelForm):
                class Meta:
                    model = self.model
                    fields = "__all__"
                    labels = {
                        ""
                    }
            return ModelFormDemo
        else:
            return self.modelform_class

    # 封装的form 方法
    def get_new_form(self, form):
        for bfield in form:
            # 这个可以看源码,然后类调用所需属性
            from django.forms.boundfield import BoundField
            print(bfield.field)             # 字段对象
            print("name", bfield.name)      # 字段名（字符串）
            print(type(bfield.field))       # 字段类型
            # 看源码可得 多对多和一对多是ModelChoiceFiled的类型
            from django.forms.models import ModelChoiceField
            if isinstance(bfield.field, ModelChoiceField):
                # 增加一个属性,传给前端做判断,是否显示这个 +按钮
                bfield.is_pop = True
                print("=======>", bfield.field.queryset.model)  # 一对多或者多对多字段的关联模型表
                # 通过下面两个方法,找到表和app名字
                related_model_name = bfield.field.queryset.model._meta.model_name
                related_app_label = bfield.field.queryset.model._meta.app_label
                # 拼接url传给前端
                _url = reverse("%s_%s_add" % (related_app_label, related_model_name))
                # 创建一个新的属性url 给前端调用
                bfield.url = _url + "?pop_res_id=id_%s" % bfield.name
        return form

    # 添加的视图函数
    def add_view(self, request):
        # 实例化form类对象 方便Django构建form表单
        ModelFormDemo = self.get_modelform_class()
        form = ModelFormDemo()
        # 将form对象传入函数get_new_form() 完成get请求逻辑,防止add_view这个视图里面代码缀余
        form = self.get_new_form(form)
        # POST请求
        if request.method == "POST":
            form = ModelFormDemo(request.POST)
            if form.is_valid():
                obj = form.save()       # 保存数据,并返回一个obj
                pop_res_id = request.GET.get("pop_res_id")
                # 判断是点击+按钮带参数访问,还是通过add页面直接访问的
                if pop_res_id:
                    res = {"pk": obj.pk, "text": str(obj), "pop_res_id": pop_res_id}
                    return render(request, "pop.html", {"res": res})
                else:
                    return redirect(self.get_list_url())
        return render(request, "add_view.html", locals())

    # 删除的视图函数
    def delete_view(self, request, id):
        url = self.get_list_url()
        if request.method == "POST":
            self.model.objects.filter(pk=id).delete()
            return redirect(url)
        return render(request, "delete_view.html", locals())

    # 编辑的视图函数
    def change_view(self, request, id):
        ModelFormDemo = self.get_modelform_class()
        print("=====id", id)
        edit_obj = self.model.objects.filter(pk=id).first()

        if request.method == "POST":
            form = ModelFormDemo(request.POST, instance=edit_obj)
            if form.is_valid():
                form.save()
                return redirect(self.get_list_url())

            return render(request, "add_view.html", locals())

        print("***********", edit_obj)
        form = ModelFormDemo(instance=edit_obj)
        form = self.get_new_form(form)

        return render(request, "change_view.html", locals())

    # 搜索的视图函数
    def get_serach_conditon(self, request):
        key_word = request.GET.get("q", "")
        self.key_word = key_word
        search_connection = Q()
        if key_word:
            # self.search_fields # ["title","price"]
            search_connection.connector = "or"
            for search_field in self.search_fields:
                # search_field+"__contains"  ---->  title__contains="o"   就是title字段里面包含字母o的
                search_connection.children.append((search_field + "__contains", key_word))
        return search_connection

    # 过滤filter的视图函数
    def get_filter_condition(self, request):
        filter_condition = Q()
        for filter_field, val in request.GET.items():
            if filter_field != "page":          # 明天在博客修改这个   并把crm/stark记录的博客中 因为现在网络故障啦
                filter_condition.children.append((filter_field, val))
        return filter_condition

    # 查看的视图函数
    def list_view(self, request):
        if request.method == "POST":  # action
            print("POST:", request.POST)
            action = request.POST.get("action")  # patch_init
            selected_pk = request.POST.getlist("selected_pk")
            action_func = getattr(self, action)
            queryset = self.model.objects.filter(pk__in=selected_pk)
            ret = action_func(request, queryset)
            # return ret
        # 获取serach的Q对象
        search_connection = self.get_serach_conditon(request)

        # 获取filter构建Q对象

        filter_condition = self.get_filter_condition(request)

        # 筛选获取当前表所有数据
        data_list = self.model.objects.all().filter(search_connection).filter(filter_condition)  # 【obj1,obj2,....】

        # 按这ShowList展示页面
        showlist = ShowList(self, data_list, request)

        # 构建一个查看URL
        add_url = self.get_add_url()
        return render(request, "list_view.html", locals())

    #  获取用户配置类里面的list_play[]
    def new_list_play(self):
        temp = []
        temp.append(ModelStark.checkbox)
        temp.extend(self.list_display)
        if not self.list_display_links:
            temp.append(ModelStark.edit)
        temp.append(ModelStark.deletes)
        return temp

    # 获取用户配置类里面的actions 这个列表
    def new_actions(self):
        temp = []
        temp.append(ModelStark.patch_delete)
        temp.extend(self.actions)
        return temp

    """把url进行反向解析,解耦到各自的函数中,函数中直接返回了对应的url"""
    # 获取修改页面的url
    def get_change_url(self, obj):
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label
        print("obj===========", obj)
        _url = reverse("%s_%s_change" % (app_label, model_name), args=(obj.pk,))

        return _url

    # 获删除改页面的url
    def get_delete_url(self, obj):
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label
        _url = reverse("%s_%s_delete" % (app_label, model_name), args=(obj.pk,))
        return _url

    # 获取添加页面的url
    def get_add_url(self):
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label
        _url = reverse("%s_%s_add" % (app_label, model_name))
        return _url

    # 获取查看页面的url
    def get_list_url(self):
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label
        _url = reverse("%s_%s_list" % (app_label, model_name))
        return _url

    # 用户额外添加url函数
    def extra_url(self):
        return []

    # 二级url分发函数
    def get_urls_2(self):
        temp = []
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label
        temp.append(url(r"^add/", self.add_view, name="%s_%s_add" % (app_label, model_name)))
        temp.append(url(r"^(\d+)/delete/", self.delete_view, name="%s_%s_delete" % (app_label, model_name)))
        temp.append(url(r"^(\d+)/change/", self.change_view, name="%s_%s_change" % (app_label, model_name)))
        temp.append(url(r"^$", self.list_view, name="%s_%s_list" % (app_label, model_name)))
        # 在这继承extra_url()的temp ,这样默认temp为空,其他的表的配置类没有写则无扩展的url,如果有的话则实现了扩展
        temp.extend(self.extra_url())
        return temp

    @property
    def urls_2(self):
        print(self.model)
        return self.get_urls_2(), None, None


class StarkSite(object):
    def __init__(self):
        self._registry = {}

    def register(self, model, stark_class=None):
        if not stark_class:
            stark_class = ModelStark

        self._registry[model] = stark_class(model, self)

    # 一级分发url函数
    def get_urls(self):
        temp = []
        for model, stark_class_obj in self._registry.items():
            model_name = model._meta.model_name
            app_label = model._meta.app_label
            # 分发增删改查
            temp.append(url(r"^%s/%s/" % (app_label, model_name), stark_class_obj.urls_2))

            '''
            url(r"^app01/userinfo/",UserConfig(Userinfo).urls_2),
            url(r"^app01/book/",ModelStark(Book).urls_2), 
            
        
            '''
        return temp

    @property
    def urls(self):
        return self.get_urls(), None, None


# 创建stark的一个单例对象
site = StarkSite()
