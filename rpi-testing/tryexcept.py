
if __name__ == "__main__":
    try:
        x = 5 / 0
    except ZeroDivisionError:
        print("error")
    else:
        print("ok")
