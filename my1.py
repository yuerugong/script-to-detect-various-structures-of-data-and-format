import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException


def selenium_scrape(url):
    email = "davidmoreno@72dragons.com"
    password = "DrDragon72!"

    # 设置 Chrome 选项
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # 如果不想在后台运行，去掉此行

    try:
        # 使用 Service 对象来指定 ChromeDriver 的路径
        driver = webdriver.Chrome(executable_path="/Users/gongyueru/Downloads/chromedriver-mac-arm64 2/chromedriver", options=options)
        driver.get(url)

        # 检测是否为登录页面
        if is_login_page(driver):
            print("检测到登录页面，尝试登录...")

            # 尝试登录
            login(driver, email, password)

            # 等待登录后的页面加载完成
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        # 现在我们已登录，继续处理筛选条件
        apply_filters_and_download(driver)

        driver.quit()
    except WebDriverException as e:
        print(f"Selenium 失败: {e}")


def is_login_page(driver):
    try:
        # 检测是否存在 Email 和 Password 字段
        email_field = driver.find_element(By.ID, "Email")
        password_field = driver.find_element(By.ID, "Password")
        return email_field is not None and password_field is not None
    except Exception:
        return False


def login(driver, email, password):
    try:
        # 输入邮箱和密码
        email_field = driver.find_element(By.ID, "Email")
        password_field = driver.find_element(By.ID, "Password")
        submit_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')

        email_field.send_keys(email)
        password_field.send_keys(password)

        submit_button.click()

        # 等待登录成功后的页面加载
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    except Exception as e:
        print(f"登录过程中出现错误: {e}")


def apply_filters_and_download(driver):
    wait = WebDriverWait(driver, 20)

    # 选择地点筛选条件
    try:
        print("正在尝试点击 'Advanced' 按钮以打开国家选择模态框...")

        # 尝试等待 Advanced 按钮可见
        advanced_button = wait.until(EC.element_to_be_clickable((By.ID, "BtnAdvancedCountry")))

        # 检查按钮是否可见
        if advanced_button.is_displayed():
            print("'Advanced' 按钮可见，准备点击")

            # 使用 JavaScript 点击按钮，确保可以执行点击
            driver.execute_script("arguments[0].click();", advanced_button)
            print("'Advanced' 按钮已点击，模态框应已打开")
        else:
            print("'Advanced' 按钮不可见，检查页面结构")

        # 等待模态框中的复选框出现，并选择 'ALGERIA'
        algeria_checkbox = wait.until(EC.element_to_be_clickable((By.ID, "country-SelectCountry-51")))
        algeria_checkbox.click()
        print("选择了 ALGERIA")

        # 等待页面刷新或其他进一步操作
        time.sleep(2)
        print("页面刷新完成")

        # 检查是否可以下载文件
        try:
            print("正在尝试点击 XLS 按钮...")
            # 尝试点击 XLS 按钮
            xls_button = wait.until(EC.element_to_be_clickable((By.ID, "SearchXLS")))
            xls_button.click()

            # 等待下载
            print("XLS 按钮已点击，正在等待下载...")
            time.sleep(5)

        except Exception as e:
            print(f"数据量太大，继续应用更多筛选条件: {e}")

    except Exception as e:
        # 在出现错误时打印出详细信息
        print(f"筛选应用失败: {e}")
        print("当前页面 HTML 源码:")


# 调用函数并传入目标 URL
selenium_scrape("https://cinando.com/en/Search/Companies")
