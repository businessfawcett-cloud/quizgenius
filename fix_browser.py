content = open("D:/Mcgrawhill/browser_controller.py", "r").read()
old = """self._url_keywords = url_keywords or [
            "mheducation",
            "mcgraw",
            "connect",
            "learning.mheducation",
        ]"""
new = """self._url_keywords = url_keywords or [
            "mheducation",
            "mcgraw",
            "connect",
            "learning.mheducation",
            "ezto.mheducation",
        ]"""
if old in content:
    content = content.replace(old, new)
    open("D:/Mcgrawhill/browser_controller.py", "w").write(content)
    print("Updated")
else:
    print("Not found")
