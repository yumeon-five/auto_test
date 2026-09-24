import allure
import pytest

from common.readyaml import get_testcase_yaml
from base.apiutil import RequestBase
from base.generateId import m_id, c_id

# 执行顺序：由 conftest.py 的 pytest_collection_modifyitems 读取
#   login(0) 登录拿 token -> User(10) 用户增删改查 -> Business(20) 下单流程
# 为什么模块内不再写 @pytest.mark.run(order=N)：那个标记要装 pytest-ordering 插件才生效，
# 本项目的 pytest 9 没装（该插件已多年不维护），写了也是静默失效、容易误判顺序，
# 所以统一改用 CHAIN_ORDER —— 模块内则依赖 pytest 自身的"按定义顺序执行"。
CHAIN_ORDER = 10


@allure.feature(next(m_id) + '用户管理模块（单接口）')
class TestUserManager:

    # 场景，allure报告的目录结构
    @allure.story(next(c_id) + "新增用户")
    # 参数化，yaml数据驱动
    @pytest.mark.parametrize('base_info,testcase', get_testcase_yaml("./testcase/User/addUser.yaml"))
    def test_add_user(self, base_info, testcase):
        allure.dynamic.title(testcase['case_name'])
        RequestBase().specification_yaml(base_info, testcase)

    @allure.story(next(c_id) + "修改用户")
    @pytest.mark.parametrize('base_info,testcase', get_testcase_yaml("./testcase/User/updateUser.yaml"))
    def test_update_user(self, base_info, testcase):
        allure.dynamic.title(testcase['case_name'])
        RequestBase().specification_yaml(base_info, testcase)

    @allure.story(next(c_id) + "删除用户")
    @pytest.mark.parametrize('base_info,testcase', get_testcase_yaml("./testcase/User/deleteUser.yaml"))
    def test_delete_user(self, base_info, testcase):
        allure.dynamic.title(testcase['case_name'])
        RequestBase().specification_yaml(base_info, testcase)

    @allure.story(next(c_id) + "查询用户")
    @pytest.mark.parametrize('base_info,testcase', get_testcase_yaml("./testcase/User/queryUser.yaml"))
    def test_query_user(self, base_info, testcase):
        allure.dynamic.title(testcase['case_name'])
        RequestBase().specification_yaml(base_info, testcase)
