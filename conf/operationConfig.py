"""用来读取配置文件"""
import configparser
from conf.setting import FILE_PATH

class OperationConfig:
    """封装读取conf.ini配置文件"""

    def __init__(self,file_path=None):

        if file_path is None:
            self.__file_path=FILE_PATH['conf']
        else:
            self.__file_path=file_path
        self.conf=configparser.ConfigParser()
        try:
            # 用 utf-8-sig 读：它同时兼容「带 BOM」和「不带 BOM」的 UTF-8 文件。
            # 用记事本另存、或用 PowerShell 的 Set-Content -Encoding UTF8 生成的 conf.ini
            # 开头会带 BOM（EF BB BF），按普通 utf-8 读出来第一个 key 变成 '\ufeff[api_envi]'，
            # configparser 直接抛「File contains no section headers」，
            # 上层只看到 host=None，最后表现成 "Invalid URL 'None/dar/user/login'" 这种看不出根因的报错。
            self.conf.read(self.__file_path,encoding='utf-8-sig')
        except Exception as e:
            print(e)

    def get_section_for_data(self,section,option):
        """
        读取conf.ini数据文件
        :param section:conf.ini的头部值 例子:[api_envi]
        :param option:选项值的key  例子：host
        :return:
        """
        try:
            data=self.conf.get(section,option)
            return data
        except Exception as e:
            print(e)

    def get_envi(self,option):
        """获取接口服务器的ip地址"""
        return self.get_section_for_data('api_envi',option)

    def get_login_conf(self,option):
        """获取业务前置登录账号信息（[LOGIN] 段），供 conftest.py 的 login_first 夹具使用"""
        return self.get_section_for_data('LOGIN',option)

    def get_clean_conf(self,option):
        """获取测试数据清理配置（[CLEAN] 段），供 common/clean_data.py 使用"""
        return self.get_section_for_data('CLEAN',option)

    def get_db_conf(self,option):
        """获取数据库断言配置（[DB] 段），供 common/connection.py 选择 sqlite / mysql 使用"""
        return self.get_section_for_data('DB',option)

    def get_mysql_conf(self,option):
        """获取Mysql配置信息"""
        return self.get_section_for_data('MYSQL',option)

    def get_section_jenkins(self,option):
        """获取Jenkins配置信息"""
        return self.get_section_for_data('JENKINS',option)

    def get_redis_conf(self,option):
        """获取redis配置信息"""
        return self.get_section_for_data('REDIS',option)

    def get_feishu_conf(self, option):
        """获取飞书通知配置（[FEISHU] 段），供 common/feishu.py 使用"""
        return self.get_section_for_data('FEISHU', option)


if __name__ == '__main__':
    oper=OperationConfig()
    print(oper.get_section_for_data('api_envi', 'host'))
    print(oper.get_envi('host'))