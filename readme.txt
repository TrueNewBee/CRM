2019-2-14 15:41:39
�����û�: yuan  yuan123
crm��Ŀ:
	1. ����stark���:	
		1. ��stark���������!
		2. ��setting����ע��stark��app  'stark.apps.StarkConfig',
		3. ��crmĿ¼�д���stark.py
		4. �ڸñ��е���starkģ��,Ȼ��ע����������

		site.register(UserInfo, UserConfig) 
	
	2. ����rbac���û���֤���
	
		1. ��rbac����������
		2. ��setting��ע��һ�²������м����ע��һ�� 	
		'rbac.apps.RbacConfig',
		'rbac.service.rbac.ValidPermission'
		3. ͨ��stark ���ʶ�Ӧurl������û�����
		4. stark/rbac/permissiongroup
		   stark/rbac/user
		   stark/rbac/permission
	           stark/rbac/role
		5. ��crm��UserInfo����rbac��user��һ��һ����
			����crm��UserInfo�������
			user = models.OneToOneField(to=User, null=True)
		
		6. ��������ݺ���Ҫ��crm�û����е����ݱ༭һ��,ʵ����һ��Ӧ
		7. Ȼ��Ϳ���ʵ�ֵ������ҪȨ����!!!!