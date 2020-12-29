# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class ContentFSMBaseException(Exception):
    def __init__(self, *args):
        self.args = args


class ContentFSMEventError(ContentFSMBaseException):
    def __init__(self, event):
        self.args = ('Event Error', event)
        self.message = "Unknow Event"
        self.code = -1


class ContentFSMTransitionError(ContentFSMBaseException):
    def __init__(self, event, from_state):
        self.args = ('Transition Error', event, from_state)
        self.message = "Transition Error"
        self.code = -2

class ContentFSMConditionError(ContentFSMBaseException):
    def __init__(self, event, condition_return_key):
        self.args = ('ConditionError Error', event, condition_return_key)
        self.message = "Condition Error"
        self.code = -3



class BaseContentFSM(object):
    """
        Features：
            1. support state protect
            2. support process-stream convergence
            2. fsm type1: event: state1 + action > state2 (> next-action)
            3. fsm type2: event: state1 > state2 (> next-action)
            4. fsm type3: event: state1 + action >  action_callback > state2 (> next-action)

        fsm type2 is not applicable for auto process-stream
        In fact, state bits should be able to indicate the arbitrariness of a thing.
        we do operation A on a video, there should be 3 states: state_for_a, state_a_processing, state_a_end,
        if the process-stream is go , A->B the state_for_b replace the state state_a_end, becoming:
        state_for_a -> state_a_processing -> state_for_b
        if the process-stream has no rest, the state transitions make this sence: state_a_processing -> state_b_processing

        content-process-stream:
        before audit: upload -> get_video_info -> dedup_md5 -> dedup_all -> get_frame_info -> detection
        audit: audit1st -> edit -> audit2st
        release: encode -> watermark + snapshot + push_backend

        changes:
            1.2019.02.27 add conditions
    """
    event_name_list = []
    event_name_config_map = {}
    def __init__(self, biz_id, config, get_state, set_state):
        for event in config['events']:
            self.event_name_list.append(event['name'])
            self.event_name_config_map[event['name']] = event
        self._biz_id = biz_id
        self._get_state_handler = get_state
        self._set_state_handler = set_state

    def _refresh(self):
        pass

    def _get_state(self):
        return self._get_state_handler(self._biz_id)

    def _set_state(self, state, *args, **kwargs):
        return self._set_state_handler(self._biz_id, state, *args, **kwargs)


    @classmethod
    def protect(self, fsm, ifrom):
        """
        state transition safe check
        :param ifrom: from state
        :param ito: to state
        :return: True,None: normal False,Info: unnormal
        """
        return True if '*' in fsm.get('from', []) or ifrom in fsm.get('from', []) else False


    def transition(self, event, *args, **kwargs):
        """
        state transition
        :param ifrom: from state
        :param event: reveive event
        :return: fsm rule
        """
        if event not in self.event_name_list:
            raise ContentFSMEventError(event)
        condition = self.event_name_config_map[event]['condition']
        transition_key = "default"
        if "func" in condition and condition["func"] is not None:
            transition_key = self._eval(condition["func"],self._biz_id, *args, **kwargs)
            print(transition_key)
            if transition_key not in condition["transitions"]:
                raise ContentFSMConditionError(event, transition_key)
        return self.event_name_config_map[event]['condition']['transitions'][transition_key]


    def deal(self, event, *args, **kwargs):
        """
        state transition
        :param ifrom: from state
        :param event: reveive event
        :return:
        """
        _fsm = self.transition(event, *args, **kwargs)
        ito = _fsm.get('to', None)
        if ito is None:
            pass
        else:
            ifrom = self._get_state()
            safe = BaseContentFSM.protect(_fsm, ifrom)
            if not safe:
                raise ContentFSMTransitionError(event, ifrom)
            else:
                pre_action = _fsm.get('pre-action', None)
                pre_action_type = _fsm.get('pre-action-type', 'func')
                self._exe_action(pre_action_type, pre_action, *args, **kwargs)
                self._set_state(ito,*args,**kwargs)
        action_next = _fsm.get('next-action', None)
        action_next_type = _fsm.get('next-action-type', 'celery')
        if action_next:
            # self._eval_task(action_next, self._biz_id, *args, **kwargs)
            # action_next(self._biz_id)
            self._exe_action(action_next_type, action_next, *args, **kwargs)

    def _exe_action(self,action_type,actions, *args, **kwargs):
        """
        pre-action  目前只支持 action_type = func
        next-action 目前只支持 action_type = celery
        """
        if type(actions) == list:
            for action_next in actions:
                if action_type == 'celery':
                    self.eval_task(action_next, self._biz_id, *args, **kwargs)
                    pass
                elif action_type == 'func':
                    self._eval(action_next, self._biz_id, *args, **kwargs)
        elif type(actions) == str:
            action_next = actions
            if action_type == 'celery':
                self.eval_task(action_next, self._biz_id, *args, **kwargs)
                pass
            elif action_type == 'func':
                self._eval(action_next, self._biz_id, *args, **kwargs)

    def eval_task(self, func, biz_id, *args, **kwargs):
        """ execute func in config in string """
        if '.' in func:
            func_split = func.split('.')
            pre_path = '.'.join(func_split[0:-1])
            task_func = func_split[-1]
            exec("from " + pre_path + " import " + task_func)
            # exec(task_func + ".delay(biz_id)")
            eval(task_func).delay(biz_id, *args, **kwargs)
        else:
            exec("import " + func)
            # exec(func + ".delay(biz_id)")
            eval(func).delay(biz_id, *args, **kwargs)

    def _eval(self, func, biz_id, *args, **kwargs):
        """ execute func in config in string """
        rtn_val = ''
        if '.' in func:
            func_split = func.split('.')
            pre_path = '.'.join(func_split[0:-1])
            task_func = func_split[-1]
            exec("from " + pre_path + " import " + task_func)
            # exec("rtn_val = "+task_func + "(biz_id)")
            rtn_val = eval(task_func)(biz_id, *args, **kwargs)
        else:
            exec("import " + func)
            # exec("rtn_val = "+func + ".delay(biz_id)")
            rtn_val = eval(func).delay(biz_id, *args, **kwargs)
        return rtn_val


