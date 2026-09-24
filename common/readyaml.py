"""
3.获取yaml文件数据，写入yaml文件数据
"""
import os
import yaml
from conf.setting import FILE_PATH


def get_testcase_yaml(file):
    """
    获取yaml文件的数据，统一展开成 [baseInfo, testCase] 的列表

    :param file:yaml文件的路径
    :return: [[base_info, test_case], [base_info, test_case], ...]

    修复记录：原实现只在「只有一个接口块」时才展开（len(yaml_data) <= 1），
    一旦文件里写了两个顶层 baseInfo 块（同一个接口的不同请求头，例如带 token / 不带 token），
    就会走 else 分支把原始结构直接返回，测试模块里 `base_info, testcase = data[0]`
    解包出来的是字典的 key（字符串 'baseInfo' / 'testCase'），后续报错完全指不到根因。
    现在改为按顶层块逐个展开，单块 / 多块文件的行为完全一致。
    """
    testcase_list = []
    try:
        # utf-8-sig：兼容带 BOM 的 UTF-8 用例文件（记事本 / PowerShell 另存就会带 BOM）。
        # 带 BOM 时 PyYAML 会报 "special characters are not allowed"，同样看不出根因
        with open(file,'r',encoding='utf-8-sig') as f:
            yaml_data = yaml.safe_load(f)
            for block in yaml_data:
                base_info = block.get('baseInfo')
                for ts in block.get('testCase'):
                    params = [base_info,ts]
                    testcase_list.append(params)
            return testcase_list
    except Exception as e:
        print(e)

class ReadYamlData(object):
    """读取yaml数据，以及写入数据到yaml文件"""
    def __init__(self,yaml_file=None):
        if yaml_file is not None:
            self.yaml_file = yaml_file
        else:
            self.yaml_file = '../testcase/login/login.yaml'
    def write_yaml_data(self,value):
        """
        写入数据到yaml文件
        :param value: (dict)写入的数据
        :return:
        """
        file=None
        file_path= FILE_PATH['extract']
        if not os.path.exists(file_path):
            os.system(file_path)
        try:
            file=open(file_path,'a',encoding='utf-8')
            if isinstance(value,dict):
                write_data=yaml.dump(value,allow_unicode=True,sort_keys=False)
                file.write(write_data)
            else:
                print('写入【extract.yaml】文件的格式为字典类型')
        except Exception as e:
            print(e)
        finally:
            file.close()

    def get_extract_yaml(self,node_name):
        """
        读取接口提取的变量值
        :param node_name:yaml文件的key值
        :return:
        """
        file_path= FILE_PATH['extract']
        if os.path.exists(file_path):
            pass
        else:
            print("extract.yaml文件不存在")
            with open(file_path, 'w', encoding='utf-8'):
                pass
            print('extract.yaml文件创建成功!')
        # utf-8-sig 同上：extract.yaml 是人工也可能打开的中间文件，带 BOM 时也要能读
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            extract_data=yaml.safe_load(f) or {}
            # 取不到变量时给出能定位的报错：接口关联依赖「前面的用例先执行并提取」这个变量。
            # 例如单独跑 testcase/asn/test_asn_detail.py（-k 筛选或直接指定文件）时，
            # 因为没有先跑 test_asn_create.py 生成 asn_code，这里就取不到；
            # 原来只抛一个 KeyError: 'asn_code'，看不出是执行顺序问题还是变量名写错了。
            if node_name not in extract_data:
                raise KeyError(
                    f'extract.yaml 里没有 "{node_name}"。接口关联依赖前面的用例先执行并提取该变量，'
                    f'当前已提取的变量：{list(extract_data.keys())}。'
                    f'（例如只跑 testcase/asn/test_asn_detail.py 时，需要先跑 testcase/asn/test_asn_create.py）')
            return extract_data[node_name]

    def clear_yaml_data(self):
        """清空extract.yaml文件的内容，目的：重新写入覆盖之前的内容，防止占用空间"""
        with open(FILE_PATH['extract'], 'w', encoding='utf-8') as f:
            f.truncate()

if __name__ == '__main__':
    # SendRequest 仅演示代码使用，放在此处导入，避免与 sendrequests 循环导入
    from common.sendrequests import SendRequest
    res=get_testcase_yaml('../testcase/login/login.yaml')[0]
    url=res['baseInfo']['url']
    new_url='http://127.0.0.1:8008'+url
    method=res['baseInfo']['method']
    data=res['testCase'][0]['data']


    sendrequest = SendRequest()
    res = sendrequest.run_main(url=new_url,data=data,header=None,method=method)
    # print(res)

    # token = res.get('token')
    # write_data={}
    # write_data['Token']=token
    # read=ReadYamlData()
    # read.write_yaml_data(write_data)

    read=ReadYamlData()
    print(read.get_extract_yaml('Token'))