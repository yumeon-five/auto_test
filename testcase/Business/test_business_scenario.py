import allure
import pytest

from common.readyaml import get_testcase_yaml
from base.apiutil_business import RequestBase
from base.generateId import m_id, c_id

# 注意：业务场景（一条用例串多个接口）要调用 base 目录下的 apiutil_business 文件，
# 它提供单参数入口 specification_yaml(case_info)，内部复用 BaseRequest 的请求与断言逻辑。

# 执行顺序：由 conftest.py 的 pytest_collection_modifyitems 读取
#   login(0) 登录拿 token -> User(10) 用户增删改查 -> Business(20) 下单流程
# 这里的 5 个接口本来就是一个参数化函数（yaml 里 5 个块），
# 参数化顺序 = yaml 里的书写顺序，而链路依赖上一步的产物：
#   商品列表(取 goodsIds) -> 商品详情 -> 提交订单(取 orderNumber/userId) -> 订单支付 -> 校验订单状态
CHAIN_ORDER = 20


@allure.feature(next(m_id) + '电子商务管理系统（业务场景）')
class TestEBusinessScenario:

    @allure.story(next(c_id) + '商品列表到下单支付流程')
    @pytest.mark.parametrize('case_info', get_testcase_yaml('./testcase/Business/BusinessScenario.yml'))
    def test_business_scenario(self, case_info):
        # get_testcase_yaml 展开后的 case_info 是 [base_info, test_case] 两元素列表，
        # 所以这里用下标取接口名（原来写成 case_info['baseInfo'] 会直接抛
        # TypeError: list indices must be integers or slices, not str，5 条业务用例全部报错）
        allure.dynamic.title(case_info[0]['api_name'])
        RequestBase().specification_yaml(case_info)
