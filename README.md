# ifsm

**ifsm** 是一个简单的FSM（有限状态机）实现. 

## 介绍

#### 概念

+ state: 实例的状态
+ event: 接收到的事件
+ action: 状态变换前后执行的操作
+ condition: 事物接收到同一事件，但是基于当前的状态及其他变量取值可以进不不同的transitions.
+ transitions: 事物接收到事件后进行状态的变更。

---

![](https://raw.githubusercontent.com/diaohaha/ifsm/master/ext/ifsm.jpg)


状态机中一次状态的转换（transitions）为：

+ 1.接收event;
+ 2.判断condition;
+ 3.执行pre-action;变换状态;执行next-action;


#### 特性

+ 状态保护: 在一些复杂的场景中，内容接收到非预期的事件，也可能接收到重复事件，状态机通过配置from状态集来判断是否为正常的流转否则抛出ContentFSMTransitionError。
+ 支持Celery: 事物的状态变更之后，可能需要一些其他的操作，但是又不想占用本次请求的时间，可以将action_type配置成celery来进行任务的异步执行，但是这将无法保证事务一致性。

## 安装

ifsm is available on PyPI:

```console
$ python -m pip install ifsm 
```


## 示例

以评论审核场景介绍ifsm使用

定义评论实例，一个评论实例对应一个状态机实例。

```python
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
```

定义状态机配置文件。


```python
STATE_UN_AUDIT = 0  # 未审核
STATE_PASS = 1     # 审核通过
STATE_AUDIT = 2    # 审核中
STATE_REJECT = 99  # 审核拒绝

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

```

重载状态机，传入获取状态和设置状态的方法，和状态变更配置文件，通常状态存在db中。


```python
from ifsm import BaseContentFSM

class CommentFSM(BaseContentFSM):
    def __init__(self, content_id):
        def get_audit_state(content_id):
            contentObj = Comment(content_id)
            return contentObj.get_state()

        def set_audit_state(content_id, state):
            contentObj = Comment(content_id)
            contentObj.set_state(state)

        super(CommentFSM, self).__init__(content_id, FSM_CONFIG, get_audit_state, set_audit_state)

```

编写condition函数和action函数

```python

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
```


业务场景中，有事件触发的时候触发状态机变更。

```python
comment = Comment("12345")
comment.set_state(STATE_UN_AUDIT)
fsm = CommentFSM(comment.get_id())
print("评论状态:" + str(comment.get_state()))
fsm.deal("audit_pass")
print("评论状态:" + str(comment.get_state()))
fsm.deal("audit_pass")
print("评论状态:" + str(comment.get_state()))
```