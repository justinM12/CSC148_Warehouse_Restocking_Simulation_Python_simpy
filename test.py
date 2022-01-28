import simpy

env = simpy.Environment()

def test():
    print("Test")

def eCause(s):
    yield env.timeout(5)
    s.interrupt()
    test()
    print("pf eCause finished at time {0}".format(env.now))

def eWait():
    while True:
        try:
            yield env.timeout(1)
        except simpy.Interrupt as interruptMsg:
            break

    print("pf eWait finished at time {0}".format(env.now))

if __name__ == "__main__":
    se = env.process(eWait())
    env.process(eCause(se))
    env.run()

    print("Model ended at: {0}".format(env.now))
    string = "aaa bbb"
    print(string[1:])