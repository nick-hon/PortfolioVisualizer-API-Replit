# FlaskApp

使用 Python Flask App

## 以下所會執行的動作

- 測試 Python Flask 伺服器

### 需求安裝

Python : 3.8

virtualenv

### 指令

1.  安裝 virtualenv (PATH 位置確定執行於 python:3.8):

        pip install virtualenv

2.  建立 Python 虛擬環境:

        virtualenv .venv

3.  進入 virtualenv:

    `powershell:`

        ./.venv/Scripts/Activate.ps1

4.  確認版本:

        python -V

    > => Python 3.8.0

        pip -V

    > => pip 22.3.1 from ~:\~\Portfoliovisualize-eb-docker\.venv\lib\site-packages\pip (python 3.8)

5.  安裝所需的 Package:

        pip install -r ./requirements.txt

6.  本地測試:

    - 啟動伺服器 main.py

      python ./main.py

      API URL: http://localhost:8080/

      測試完成後關閉伺服器

7.  退出 virtualenv

        deactivate

#### 其他指令

- 製作 requirements.txt

        pip freeze > requirements.txt
