import os
import pytest
import time
import requests
from common.recordlog import logs
from common.readyaml import ReadYamlData
from common.feishu import send_fs_msg
from common.operJenkins import OperJenkins
from conf.operationConfig import OperationConfig
from conf.setting import FILE_PATH

read=ReadYamlData()

# 不参与采集的目录（路径相对本文件所在的项目根目录）。
#
# testcase/ProductManager 里是「商品列表 / 商品详情 / 提交订单 / 订单支付」四个接口，
# 和 testcase/Business 的「下单流程」接口完全重叠，属于同一批接口的两种写法。
# 当前只跑三个模块：testcase/login（登录）、testcase/User（用户单接口）、
# testcase/Business（下单流程），所以先把这份重名的用例排除掉，
# 否则同一个接口会跑两遍，报告里也会出现两套结果。
# 以后要启用它，把下面这行注释掉即可 —— 但注意 getProductList.yaml 里写的是
# ${get_extract_data(cookie)}，login 用例提取的变量名是 token，需要同步改成 token。
collect_ignore_glob = ['testcase/ProductManager/*']

# 自己记录会话开始时间，避免依赖 pytest 内部属性（不同版本类型不一致：float/Instant）
_SESSION_START_TIME = time.time()


def pytest_sessionstart(session):
    """pytest 会话开始时触发，记录开始时间戳"""
    global _SESSION_START_TIME
    _SESSION_START_TIME = time.time()


@pytest.fixture(scope='session', autouse=True)
def clear_extract_data():
    """前置操作：清除extract.yaml文件中的数据"""
    read.clear_yaml_data()


def do_login(host, username, password, timeout=10):
    """
    调用电商项目的登录接口，成功返回 (token, userId)，失败抛 AssertionError（带可读原因）。

    接口契约（flask 服务 base/flask_service.py 的 user_login）：
      POST /dar/user/login，form 表单（application/x-www-form-urlencoded）
      参数：user_name / passwd
      成功：{"msg": "登录成功", "msg_code": 200, "token": "<29位>", "userId": "...", "orgId": "..."}
      失败：{"msg": "登录失败,用户名或密码错误", "msg_code": 9001, "token": null, "userId": null}
      少参数：{"msg": "参数错误", "msg_code": -1}

    单独抽成函数是因为要登录两次：会话开始时一次（快速失败），每个用例前再一次（刷新 token）。
    """
    url = f'{host}/dar/user/login'
    try:
        # 必须是 form 表单：被测接口用 flask.request.form.get('user_name') 取值，
        # 换成 json= 传参接口侧取不到值，会返回「参数错误」
        res = requests.post(url, data={'user_name': username, 'passwd': password}, timeout=timeout)
    except Exception as e:
        raise AssertionError(f'登录请求异常：{url} -> {e}\n'
                             f'（最常见的场景：被测的 flask 服务没启动，默认监听 127.0.0.1:8787）')

    # 接口返回非 JSON（404 页面 / 500 错误页）时，给出能直接定位问题的报错，
    # 而不是让 res.json() 抛 JSONDecodeError 这种看不出根因的异常
    try:
        res_json = res.json()
    except ValueError:
        raise AssertionError(f'登录返回的不是 JSON，请确认接口地址与后端服务是否正常：{url}\n'
                             f'HTTP {res.status_code}\n响应内容：{res.text[:500]}')

    token = res_json.get('token')
    if str(res_json.get('msg_code')) != '200' or not token:
        raise AssertionError(f'登录失败：url={url}，账号={username}\n'
                             f'响应={res_json}\n'
                             f'（请检查 conf/conf.ini 的 [LOGIN] 账号密码是否正确，'
                             f'电商 flask 服务的固定账号见 flask_service.py 的 user_info）')
    return token, res_json.get('userId')


@pytest.fixture(scope='session', autouse=True)
def login_first(clear_extract_data):
    """
    业务线前置：会话开始先登录一次，把 token / userId 写入 extract.yaml。

    为什么需要：testcase/User/addUser.yaml 里写了 ${get_extract_data(token)} 做接口关联，
    而 clear_extract_data 每次会话都会清空 extract.yaml，因此必须先登录拿凭证；
    否则 get_extract_data('token') 会抛 KeyError: 'token'。
    显式依赖 clear_extract_data，保证「先清空、再登录」的顺序。

    这里的主要价值是「快速失败」：服务没起来、账号密码配错，会在会话最开头
    以一句能看懂的报错结束，而不是让一堆用例各自报 KeyError: 'token'。

    修复记录：
    1) 这个夹具原来请求 WMS 的 /login/ + JSON 参数 name/password；现在项目换回电商，
       改回 /dar/user/login + form 参数 user_name/passwd。
    2) 原来失败只 log.error 不抛异常，属于静默失败：依赖 token 的模块会在后面
       以 KeyError: 'token' 这种毫不相干的报错挂掉。现在改为 pytest.fail 快速失败。
    """
    # 前置检查：conf/conf.ini 是本地环境配置，不入库，新环境 clone 后要先从模板复制一份。
    # 缺文件时 configparser 不会抛异常（read 会静默忽略不存在的文件），只会让 host 读成 None，
    # 最后表现成 "Invalid URL 'None/dar/user/login'" 这种看不出根因的报错，所以在这里提前拦一下。
    if not os.path.exists(FILE_PATH['conf']):
        pytest.fail(f'配置文件不存在：{FILE_PATH["conf"]}\n'
                    f'请复制 conf/conf.ini.example 为 conf/conf.ini，并按实际环境填写。')

    config = OperationConfig()
    host = config.get_envi('host')
    # 账号密码统一放在 conf/conf.ini 的 [LOGIN] 段，代码里不再硬编码
    username = config.get_login_conf('username')
    password = config.get_login_conf('password')
    try:
        token, user_id = do_login(host, username, password)
    except AssertionError as e:
        pytest.fail(str(e))

    read.write_yaml_data({'token': token, 'userId': user_id})
    logs.info(f'前置登录成功，token / userId 已写入 extract.yaml：{token} / {user_id}')


@pytest.fixture(scope='function', autouse=True)
def refresh_login_token(login_first):
    """
    每个用例执行前刷新一次登录 token（写入 extract.yaml 的 token 字段）。

    为什么必须这么做 —— 被测服务的 token 是"全局唯一"的，而且会被任何一次登录请求覆盖：

        flask_service.py 的 user_login 里，global_params['token'] = token 写在密码校验之前，
        也就是说哪怕账号密码错了、参数少了，这一次请求生成的新 token 照样会覆盖服务端的全局值；
        而 /dar/user/addUser 校验的正是这个全局值（token == global_params['token']）。

    于是出现一个很隐蔽的连锁反应：testcase/login 里的失败用例（密码错误 / 用户不存在）
    跑完之后，服务端认的 token 已经不是 extract.yaml 里那个了，
    后面「新增用户」拿旧 token 去校验，只能得到 token 失效 —— 用例本身没问题，是数据被污染了。
    实测（对着 127.0.0.1:8787 验证的三种组合）：
        成功登录拿 t1 -> 立刻用 t1 新增   = 新增成功
        成功登录拿 t1 -> 夹一次失败登录 -> 用 t1 新增 = 新增失败，参数缺失或token失效
        重新成功登录拿 t2 -> 用 t2 新增   = 新增成功

    结论：需要凭证的用例必须"先登录、紧接着调用"，所以这里在每个用例前刷新一次。
    代价是每个用例多一次登录请求（本地几毫秒），换来的是用例之间不再互相污染 ——
    不管以后谁在用例中间调了登录接口，都不会影响其它用例。

    注意两点：
    1) 这里只写 token，不写 userId。电商链路用例（提交订单 -> 订单支付）自己会提取 userId，
       extract.yaml 是追加写入、同名 key 以最后一次为准，多写一次会把链路的取值覆盖掉。
    2) 刷新失败只告警不抛异常：服务整体不可用时，login_first 在会话开始就已经失败了；
       这里再抛会让每个用例都变成"夹具报错"，反而看不出真正失败的用例。
    """
    config = OperationConfig()
    host = config.get_envi('host')
    username = config.get_login_conf('username')
    password = config.get_login_conf('password')
    try:
        token, _ = do_login(host, username, password)
        read.write_yaml_data({'token': token})
    except AssertionError as e:
        logs.warning(f'用例前置 token 刷新失败，本次继续使用 extract.yaml 里已有的 token：{e}')


def pytest_collection_modifyitems(config, items):
    """
    按测试模块声明的 CHAIN_ORDER 排序，保证「链路用例」按业务顺序执行。

    为什么需要：pytest 默认按文件名 + 采集顺序执行，而模块之间有先后依赖：
      login(0) 登录拿 token -> User(10) 用户增删改查 -> Business(20) 商品列表到下单支付

    用法：在测试模块顶部声明链路序号，例如 testcase/User/test_debug_api.py 里写
    CHAIN_ORDER = 10。没声明的模块取默认值 1000（排在最后）；
    sort 是稳定排序，同序号的模块保持原有相对顺序（模块内的方法仍按定义顺序执行）。
    """
    def chain_order(item):
        module = getattr(item, 'module', None)
        return getattr(module, 'CHAIN_ORDER', 1000)

    items.sort(key=chain_order)


@pytest.fixture(scope='session',autouse=True)
def fixture_test():
    """前后置处理"""
    logs.info('----------------------接口测试开始---------------------')
    yield
    logs.info('----------------------接口测试结束---------------------')

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """
    pytest内置的钩子函数，函数名为固定写法，不可以变更
    每次pytest测试完成后，会自动收集测试结果的数据
    :param terminalreporter: 内部终端报告对象，对象的stats属性
    :param exitstatus:将报告返回操作系统的退出状态
    :param config:pytest配置对象
    :return:
    """
    print(terminalreporter.stats)
    #收集测试用例总数
    case_total = terminalreporter._numcollected
    print(f'测试用例总数:{case_total}')
    #收集测试用例通过数
    passed=len(terminalreporter.stats.get('passed',[]))
    print(f'测试用例通过数:{passed}')
    # 收集测试用例失败数
    failed=len(terminalreporter.stats.get('failed',[]))
    print(f'测试用例失败数:{failed}')
    #收集测试用例错误数
    error=len(terminalreporter.stats.get('error',[]))
    print(f'测试用例错误数:{error}')
    #收集测试用例跳过数
    skipped=len(terminalreporter.stats.get('skipped',[]))
    print(f'测试用例跳过数:{skipped}')
    duration = time.time() - _SESSION_START_TIME
    print(f'测试用例执行时常:{duration:.2f}s')
    # Jenkins / 飞书属于外部通知服务，失败时不应影响 pytest 收尾
    report = '未获取到报告链接'
    try:
        oper = OperJenkins()
        report = oper.report_success_or_fail()
    except Exception as e:
        # 关键：这里绝对不能 return！
        # 原来写成 return，导致「Jenkins 拿不到报告链接」时整条飞书通知都不发了 ——
        # 通知里少一个链接可以接受，一条通知都不发才是真问题
        logs.warning(f'获取 Jenkins 测试报告链接失败，通知里将不带链接：{e}')
    content = f"""
    自动化测试结果，通知如下，请着重关注测试失败的接口，具体执行结果如下：
    测试用例总数：{case_total}
    测试通过数：{passed}
    测试失败数：{failed}
    错误数量：{error}
    跳过执行数量：{skipped}
    执行总时长：{duration}
    点击查看测试报告：{report}
    """
    try:
        # 只有失败/错误时才 @所有人：定时构建每天都 @ 全员会很烦，全绿时安静一点
        send_fs_msg(content, at_all=(failed + error) > 0)
    except Exception as e:
        logs.warning(f'发送飞书通知失败：{e}')
