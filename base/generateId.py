def generate_module_id():
    """
    生成测试模块编号，为了保证allure报告的顺序与pytest设定的执行顺序一致
    :return:
    """
    for i in range(1,1000):
        module_id='M'+str(i).zfill(2)+'_'
        yield module_id

def generate_testcase_id():
    """
    生成测试用例编号
    :return:
    """
    for i in range(1,1000):
        case_id='C'+str(i).zfill(2)+'_'
        yield case_id

m_id = generate_module_id()
case_id = generate_testcase_id()

# 兼容电商项目用例的导入写法：testcase/User/test_debug_api.py 里写的是
#     from base.generateId import m_id, c_id
# 本框架原来导出的名字是 case_id，这里把 c_id 作为同一个生成器的别名 ——
# 两个名字共用同一个生成器对象，编号不会重复也不会跳号。
c_id = case_id