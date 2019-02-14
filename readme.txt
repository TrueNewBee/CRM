2019-2-14 15:41:39
超级用户: yuan  yuan123
crm项目:
	1. 引入stark组件:	
		1. 把stark组件考过来!
		2. 在setting里面注册stark的app  'stark.apps.StarkConfig',
		3. 在crm目录中创建stark.py
		4. 在该表中导入stark模块,然后注册表和配置类

		site.register(UserInfo, UserConfig) 
	
	2. 引入rbac的用户认证组件
	
		1. 把rbac组件导入过来
		2. 在setting中注册一下并且在中间件中注册一下 	
		'rbac.apps.RbacConfig',
		'rbac.service.rbac.ValidPermission'
		3. 通过stark 访问对应url来添加用户数据
		4. stark/rbac/permissiongroup
		   stark/rbac/user
		   stark/rbac/permission
	           stark/rbac/role
		5. 把crm的UserInfo表与rbac的user表一对一关联
			即在crm的UserInfo表中添加
			user = models.OneToOneField(to=User, null=True)
		
		6. 添加完数据后需要在crm用户表中的数据编辑一下,实现以一对应
		7. 然后就可以实现登入后需要权限啦!!!!