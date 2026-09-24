"""
业务场景（多接口链路）用例的执行入口。

为什么单独有这个文件：电商的「下单流程」用例（testcase/Business/BusinessScenario.yml）
把 5 个接口串成一条链路，测试模块里写的是单参数调用：

    RequestBase().specification_yaml(case_info)      # case_info 来自 get_testcase_yaml

而 base/apiutil.py 里的 BaseRequest.specification_yaml(base_info, test_case) 是两参数
（接口公共信息 + 单条用例），所以这里加一层适配，把单参数拆成两参数。

设计取舍：这里**继承** BaseRequest，而不是把 apiutil.py 的请求/提取/断言代码复制一份。
原因：复制一份等于同一套逻辑有两份实现，以后修 bug 要改两个地方
（原电商框架就是这个结构，apiutil.py 和 apiutil_business.py 里的 extract_data 已经不一致了）。
继承之后本文件只负责「参数形式的适配」，发请求、提取变量、断言全部复用同一份代码，
WMS 时期在 apiutil.py 里修过的那些坑（JSONPath 与 ${} 混淆、提取失败不中断、类型保持等）自动生效。
"""
import allure

from base.apiutil import BaseRequest
from common.recordlog import logs


class RequestBase(BaseRequest):

    @staticmethod
    def split_case_info(case_info):
        """
        把 get_testcase_yaml 返回的一条数据拆成 (接口公共信息, 用例列表)。

        common/readyaml.py 的 get_testcase_yaml 会把 yaml 里每个顶层块的每个 testCase
        展开成 [base_info, test_case] 两元素列表，所以这里正常收到的是：

            case_info = [ {baseInfo 的内容...}, {一条 testCase...} ]

        为了兼容原电商框架「一个 baseInfo 下挂多条 testCase」的结构，
        第二个元素是列表时也支持（等价于逐条执行）。

        :param case_info: list，形如 [base_info, test_case] 或 [base_info, [test_case, ...]]
        :return: (base_info, [test_case, ...])
        """
        if not isinstance(case_info, (list, tuple)) or len(case_info) < 2:
            raise TypeError(
                f'业务场景用例的数据格式不对，期望 [baseInfo, testCase] 两元素列表，实际收到：{case_info!r}；'
                f'请确认测试模块里用的是 get_testcase_yaml(...) 的返回值')
        base_info, test_case = case_info[0], case_info[1]
        if isinstance(test_case, list):
            test_cases = test_case
        elif isinstance(test_case, dict):
            # get_testcase_yaml 展开后的常见形态：一个块里只有一条用例
            test_cases = [test_case]
        else:
            raise TypeError(f'testCase 部分既不是字典也不是列表：{test_case!r}')
        return base_info, test_cases

    def specification_yaml(self, case_info):
        """
        业务场景用例的统一入口（单参数）

        :param case_info: [base_info, test_case] —— 直接传 get_testcase_yaml 的元素即可

        说明：BaseRequest.specification_yaml 内部会先浅拷贝一份用例数据再 pop
        case_name / validation 等字段（不会改到参数化传入的原对象），
        所以同一条用例数据重复执行也不会报 KeyError。
        """
        base_info, test_cases = self.split_case_info(case_info)
        for test_case in test_cases:
            logs.info(f'业务场景用例开始执行：{base_info.get("api_name")} -> {test_case.get("case_name")}')
            allure.attach(f'{base_info.get("api_name")} -> {test_case.get("case_name")}',
                          '业务场景用例', allure.attachment_type.TEXT)
            # 显式写 super()：本类也叫 RequestBase，避免有人误以为在递归调用自己
            super().specification_yaml(base_info, test_case)


if __name__ == '__main__':
    from common.readyaml import get_testcase_yaml
    # 调试用：单独跑一条业务场景用例
    case_datas = get_testcase_yaml('../testcase/Business/BusinessScenario.yml')
    RequestBase().specification_yaml(case_datas[0])
