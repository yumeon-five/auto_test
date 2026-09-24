import pytest
import allure

from common.readyaml import get_testcase_yaml

from base.apiutil import BaseRequest

# 模块三：登录
#
# 链路顺序：login(0) 登录拿 token -> User(10) 用户单接口 -> Business(20) 下单流程
# 由 conftest.py 的 pytest_collection_modifyitems 读取。
#
# 为什么登录必须排最前：登录接口每成功调用一次就会覆盖被测服务里的全局 token，
# 而"新增用户"接口拿用例里的 token 去和这个全局值比对。
# 登录用例跑在前面时，extract.yaml 里的 token 和服务端全局值是同一次登录的结果，
# 后面的写入类接口才能通过校验。
CHAIN_ORDER = 0

# 模块级加载用例数据，按 yaml 中的顺序索引参数化
LOGIN_CASES = get_testcase_yaml('./testcase/login/login.yaml')


@allure.feature('登录接口')  # allure报告显示
class TestLogin:

    @allure.story('用户登录校验')
    @pytest.mark.parametrize('case_index', range(len(LOGIN_CASES)))
    def test_login(self, case_index):
        base_info, testcase = LOGIN_CASES[case_index]
        # 标题加零填充序号前缀：Allure 同 suite 内按标题字母序展示，
        # 加前缀后字母序即等于 yaml 用例顺序，实现按序号排序
        allure.dynamic.title(f"{case_index + 1:02d}-{testcase['case_name']}")
        BaseRequest().specification_yaml(base_info, testcase)
