# -*- coding: utf-8 -*-


from ifsm import BaseContentFSM


STATE_UN_AUDIT = 0  # 未审核
STATE_PASS = 1     # 审核通过
STATE_AUDIT = 2    # 审核中
STATE_REJECT = 99  # 审核拒绝


def Singleton(cls):
    _instance = {}
    def _singleton(*args, **kargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kargs)
        return _instance[cls]
    return _singleton

@Singleton
class Comment(object):
    def __init__(self, content_id):
        self.content_id = content_id
        self._state = 0

    def get_id(self):
        return self.content_id

    def get_state(self):
        # get state by content_id
        # return ContentOrm.objects.get(id=self._content_id).state
        return self._state

    def set_state(self, state):
        self._state = state


class CommentFSM(BaseContentFSM):
    def __init__(self, content_id):
        def get_audit_state(content_id):
            contentObj = Comment(content_id)
            return contentObj.get_state()

        def set_audit_state(content_id, state):
            contentObj = Comment(content_id)
            contentObj.set_state(state)

        super(CommentFSM, self).__init__(content_id, FSM_CONFIG, get_audit_state, set_audit_state)

FSM_CONFIG = {
    "events": [
        {
            "name": "audit_pass",
            "condition": {
                "func": "example.audit_pass_condition",
                "transitions": {
                    "pass_at_audit_1st": {
                        "from": [STATE_UN_AUDIT, STATE_REJECT],
                        "to": STATE_PASS,
                        "next-action-type":"func",
                        "next-action": "example.audit_pass_action"
                    },
                    "pass_at_audit_2nd":{
                        "from": [STATE_AUDIT],
                        "to": STATE_PASS,
                        "next-action-type":"func",
                        "next-action": "example.audit_pass_action"
                    },
                    "to_audit_2nd": {
                        "from": [STATE_UN_AUDIT],
                        "to": STATE_AUDIT,
                        "next-action-type":"func",
                        "next-action": "example.audit_pass_to2nd_action"
                    },
                    "manual_pass": {
                        "from": ["*"],
                        "to": STATE_PASS,
                        "pre-action-type": "func",
                        "pre-action": "example.audit_pass_pre_action",
                        "next-action-type": "func",
                        "next-action": "example.audit_pass_action"
                    }
                }
            }
        },
        {
            "name": "audit_reject",
            "condition": {
                "func": "example.audit_reject_condition",
                "transitions": {
                    "default": {
                        "from": ["*"],
                        "to": STATE_REJECT,
                        "next-action-type":"func",
                        "next-action": "example.audit_reject_action"
                    },
                }
            }
        },
    ]
}


def audit_pass_condition(comment_id):
    """
    根据当前数据状态及其他变量确定所属的condition
    :param comment_id:
    :return:
    """
    return "to_audit_2nd"


def audit_pass_action(comment_id, *args, **kwargs):
    """
    审核通过后执行的操作，如记录日志，同步状态等。
    :param comment_id:
    :param args:
    :param kwargs:
    :return:
    """
    print("评论%s 审核通过！" % comment_id)

def audit_reject_action(comment_id, *args, **kwargs):
    """
    审核通过后执行的操作，如记录日志，同步状态等。
    :param comment_id:
    :param args:
    :param kwargs:
    :return:
    """
    print("评论%s 审核拒绝" % comment_id)


def audit_pass_pre_action(comment_id, *args, **kwargs):
    """
    修改状态的前置操作
    :param comment_id:
    :param args:
    :param kwargs:
    :return:
    """
    print("审核队列已移出")


def audit_pass_to2nd_action(comment_id, *args, **kwargs):
    """
    二次审核action
    :param comment_id:
    :param args:
    :param kwargs:
    :return:
    """
    print("评论%s 进入复审！" % comment_id)



comment = Comment("12345")
comment.set_state(STATE_UN_AUDIT)
fsm = CommentFSM(comment.get_id())
print("评论状态:" + str(comment.get_state()))
fsm.deal("audit_pass")
print("评论状态:" + str(comment.get_state()))
fsm.deal("audit_pass")
print("评论状态:" + str(comment.get_state()))
