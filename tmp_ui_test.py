from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    page.goto('http://localhost:5173/config/new')
    page.wait_for_load_state('networkidle')
    time.sleep(2)

    # Fill scene name
    scene_input = page.locator('input[placeholder*="销售"]')
    if scene_input.count() > 0:
        scene_input.fill('样式统一测试')
        print('[OK] 场景名称已填写')

    # Click next
    next_btn = page.locator('button:has-text("下一步")')
    if next_btn.count() > 0:
        next_btn.first.click()
        time.sleep(2)
        print('[OK] 进入 Step 2')

        # Upload file
        file_input = page.locator('input[type="file"]')
        if file_input.count() > 0:
            file_input.first.set_input_files('/Users/lixinyuan/code/CCTEST/demo/test.xlsx')
            time.sleep(3)
            page.screenshot(path='/tmp/step2_lightweight.png', full_page=True)
            print('[OK] Step 2 截图')

            # Go to step 3
            next_btn2 = page.locator('button:has-text("下一步")')
            if next_btn2.count() > 0:
                next_btn2.first.click()
                time.sleep(2)
                page.screenshot(path='/tmp/step3_lightweight.png', full_page=True)
                print('[OK] Step 3 截图')

                # Go to step 4
                next_btn3 = page.locator('button:has-text("下一步")')
                if next_btn3.count() > 0:
                    next_btn3.first.click()
                    time.sleep(1)
                    excel_option = page.locator('.cursor-pointer:has-text("Excel")')
                    if excel_option.count() > 0:
                        excel_option.first.click()
                        time.sleep(1)
                    page.screenshot(path='/tmp/step4_lightweight.png', full_page=True)
                    print('[OK] Step 4 截图')

    browser.close()
    print('\n=== 完成 ===')
