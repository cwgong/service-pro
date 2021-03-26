from LAC import LAC

def test_lac():
    lac = LAC(mode = "seg")

    text = ["下雪天适合喝一杯优乐美。","今天是个好日子"]
    seg_result = lac.run(text)
    print(seg_result)


def judge_telephone(goods_name,telephones_list,tools_list):
    pass
