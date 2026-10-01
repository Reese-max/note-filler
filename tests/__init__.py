"""測試套件 package 標記。

讓 tests/ 成為正式 package：pytest 以 ``tests.<module>`` 匯入測試
模組並把 repo root 插入 ``sys.path``，``from tests.test_pipeline
import ...`` 因此一律解析到本 checkout，不會被 sys.path 上其他的
``tests`` package（外部工具、site-packages .pth 注入的路徑）遮蔽。
"""
