# Strong

看着是个简陋的待办事项程序，但它的灵魂是完成事项会获得“经验值”，得到自我激励效果。

## 项目结构

```bash
strong/
	bluprints/  #视图函数，即接收浏览器请求的代码在这里
		auth.py		#登录、注册等用户相关的逻辑
		data.py		#为数据可视化页面提供数据处理
		task.py		#任务相关的逻辑
	static/		#静态资源，用到的css、js框架，以及项目logo等在这里
		css/	
		img/
		js/
	templates/	#模板，即html页面在这里
	uploads/	#用户上传的文件，如头像在这里
	__init__.py #工厂函数，创建app、初始化扩展
	config.py	#配置，如数据库的连接配置在这里
	manage.py  	#运行它
	...
```



## 运行项目

**1 下载代码**

直接下载压缩包到本地解压就可以。

**2 配置python环境**

需要安装python环境及其相关的依赖库。可以用conda创建一个新的python虚拟环境，python3.10.9是我使用的版本，不一定要相同。

```bash
conda create --name strong python=3.10.9
```

然后激活虚拟环境，

```bash
conda activate strong
```

在命令行中看到前面有环境名称，代表已经进入环境，如：

```
(strong) D:\code_all\code_python\Web\Strong>
```

项目中`requirements.txt`记录了我环境中所包含的python库，可以使用它将这些库安装到你的新环境中。

```bash
pip install -r requirements.txt
```

**3 配置数据库**

默认你已经安装了mysql。首先需要手动新建一个数据库，在命令行登录mysql后

```bash
mysql> create database strong;
Query Ok, 1 row affected (0.12 sec);  # 成功创建的提示
```

到项目目录下激活虚拟环境后，利用flask进行数据库的迁移，即创建程序所需要的数据表（还都只是个空表）。

```bash
flask db init		# 初始化迁移存储库，你会看到项目中多出一个migrations文件夹
flask db migrate	# 进行迁移，即在migrations中生成创建数据表所需要的脚本，你可以检查或修改它们（但一般不用）
flask db upgrade	# 执行迁移，运行刚刚生成的脚本，此时你的mysql中就有新的数据表了
```

配置数据库的连接，写上你自己mysql的用户名和密码。找到文件`config.py`，修改变量`SQLALCHEMY_DATABASE_URI`的值。文件中有`BaseConfig`和`DevelopmentConfig`两个类中都有这个变量，默认是用的base的。

```bash
SQLALCHEMY_DATABASE_URI = 'mysql://<用户名>:<密码>@127.0.0.1:3306/<数据库名字>'
```

**4 运行**

有两种方式，一种是运行`manage.py`文件，在命令行输入

```bash
python manage.py
```

另一种是使用flask命令运行，它会自动在项目的某些（忘记具体的）位置寻找名为`app`的对象，并调用它的`.run()`方法运行。

```bash
flask run
```






## 不用看

代码注释中用到的关键词：
1. 重构：代码质量有待改进的地方。
2. 问题：代码有些不懂的地方。
3. 怀疑：可能有负面影响的地方。


## 协作

@陆游气坏了 加入协作 hello

nice to meet you
