# vim: expandtab
# -*- coding: utf-8 -*-
import random

from django.db import IntegrityError
from django.test import TestCase

from poleno.timewarp import timewarp
from poleno.mail.models import Message, Recipient
from poleno.utils.date import local_datetime_from_local, naive_date
from poleno.utils.misc import flatten, Bunch
from poleno.utils.test import created_instances
from chcemvediet.apps.obligees.models import Obligee

from .. import InforequestsTestCaseMixin
from ...models import Inforequest, InforequestEmail, Branch, Action, ActionDraft

class BranchTest(InforequestsTestCaseMixin, TestCase):
    u"""
    Tests ``Branch`` model.
    """

    def test_inforequest_field(self):
        inforequest = self._create_inforequest()
        branch = self._create_branch(inforequest=inforequest)
        self.assertEqual(branch.inforequest, inforequest)

    def test_inforequest_field_may_not_be_null(self):
        with self.assertRaisesMessage(IntegrityError, u'inforequests_branch.inforequest_id may not be NULL'):
            self._create_branch(omit=[u'inforequest'])

    def test_obligee_field(self):
        inforequest = self._create_inforequest()
        branch = self._create_branch(inforequest=inforequest, obligee=self.obligee2)
        self.assertEqual(branch.obligee, self.obligee2)

    def test_obligee_field_may_not_be_null(self):
        inforequest = self._create_inforequest()
        with self.assertRaisesMessage(AssertionError, u'Branch.obligee is mandatory'):
            self._create_branch(inforequest=inforequest, omit=[u'obligee'])

    def test_historicalobligee_is_autogenerated_when_creating_new_instance(self):
        inforequest = self._create_inforequest()
        branch = self._create_branch(inforequest=inforequest, obligee=self.obligee2)
        self.assertEqual(branch.historicalobligee, self.obligee2.history.first())

    def test_historicalobligee_is_not_regenerated_when_saving_existing_instance(self):
        inforequest = self._create_inforequest()
        branch = self._create_branch(inforequest=inforequest, obligee=self.obligee2)
        branch.obligee = self.obligee1
        branch.save()
        branch = Branch.objects.get(pk=branch.pk)
        self.assertEqual(branch.historicalobligee, self.obligee2.history.first())

    def test_historicalobligee_autogenerated_value_is_current_obligee_revision(self):
        inforequest = self._create_inforequest()
        self.obligee2.name = u'Original Name'
        self.obligee2.save()
        self.obligee2.name = u'Changed Name'
        self.obligee2.save()
        branch = self._create_branch(inforequest=inforequest, obligee=self.obligee2)
        self.assertEqual(branch.historicalobligee.name, u'Changed Name')

    def test_historicalobligee_autogenerated_value_freezes_current_obligee_revision(self):
        inforequest = self._create_inforequest()
        self.obligee2.name = u'Original Name'
        self.obligee2.save()
        branch = self._create_branch(inforequest=inforequest, obligee=self.obligee2)
        self.obligee2.name = u'Changed Name'
        self.obligee2.save()
        branch = Branch.objects.get(pk=branch.pk)
        self.assertEqual(branch.historicalobligee.name, u'Original Name')

    def test_historicalobligee_may_not_be_set_explicitly(self):
        inforequest = self._create_inforequest()
        with self.assertRaisesMessage(AssertionError, u'Branch.historicalobligee is read-only'):
            self._create_branch(inforequest=inforequest, obligee=self.obligee2, historicalobligee=self.obligee2.history.first())

    def test_advanced_by_field(self):
        inforequest, branch, (request,) = self._create_inforequest_scenario()
        branch = self._create_branch(inforequest=inforequest, advanced_by=request)
        self.assertEqual(branch.advanced_by, request)

    def test_advanced_by_field_default_value_if_omitted(self):
        inforequest = self._create_inforequest()
        branch = self._create_branch(inforequest=inforequest, omit=[u'advanced_by'])
        self.assertIsNone(branch.advanced_by)

    def test_action_set_relation(self):
        _, branch, actions = self._create_inforequest_scenario(u'confirmation', u'extension')
        request, confirmation, extension = actions
        result = branch.action_set.all()
        self.assertEqual(list(result), [request, confirmation, extension])

    def test_action_set_relation_with_advancement(self):
        _, branch, actions = self._create_inforequest_scenario(u'confirmation', (u'advancement', [u'extension']), u'appeal')
        request, confirmation, (advancement, _), appeal = actions
        result = branch.action_set.all()
        self.assertEqual(list(result), [request, confirmation, advancement, appeal])

    def test_action_set_relation_empty_by_default(self):
        inforequest = self._create_inforequest()
        branch = self._create_branch(inforequest=inforequest)
        result = branch.action_set.all()
        self.assertEqual(list(result), [])

    def test_actiondraft_set_relation(self):
        inforequest, branch, _ = self._create_inforequest_scenario()
        draft1 = self._create_action_draft(inforequest=inforequest, branch=branch, type=ActionDraft.TYPES.CONFIRMATION)
        draft2 = self._create_action_draft(inforequest=inforequest, branch=branch, type=ActionDraft.TYPES.EXTENSION)
        result = branch.actiondraft_set.all()
        self.assertItemsEqual(result, [draft1, draft2])

    def test_actiondraft_set_relation_empty_by_default(self):
        _, branch, _ = self._create_inforequest_scenario()
        result = branch.actiondraft_set.all()
        self.assertItemsEqual(result, [])

    def test_inforequest_branch_set_backward_relation(self):
        inforequest, branch1, actions = self._create_inforequest_scenario(u'advancement')
        _, (_, [(branch2, _)]) = actions
        result = inforequest.branch_set.all()
        self.assertItemsEqual(result, [branch1, branch2])

    def test_inforequest_branch_set_backward_relation_empty_by_default(self):
        inforequest = self._create_inforequest()
        result = inforequest.branch_set.all()
        self.assertItemsEqual(result, [])

    def test_obligee_branch_set_backward_relation(self):
        _, branch1, _ = self._create_inforequest_scenario(self.obligee1)
        _, branch2, _ = self._create_inforequest_scenario(self.obligee1)
        result = self.obligee1.branch_set.all()
        self.assertItemsEqual(result, [branch1, branch2])

    def test_obligee_branch_set_backward_relation_empty_by_default(self):
        result = self.obligee1.branch_set.all()
        self.assertItemsEqual(result, [])

    def test_historicalobligee_branch_set_backward_relation(self):
        historicalobligee1 = self.obligee1.history.first()
        _, branch1, _ = self._create_inforequest_scenario(self.obligee1)
        self.obligee1.name = u'Changed'
        self.obligee1.save()
        historicalobligee2 = self.obligee1.history.first()
        _, branch2, _ = self._create_inforequest_scenario(self.obligee1)
        result1 = historicalobligee1.branch_set.all()
        result2 = historicalobligee2.branch_set.all()
        self.assertItemsEqual(result1, [branch1])
        self.assertItemsEqual(result2, [branch2])

    def test_historicalobligee_branch_set_backward_relation_empty_by_default(self):
        historicalobligee = self.obligee1.history.first()
        result = historicalobligee.branch_set.all()
        self.assertItemsEqual(result, [])

    def test_action_advanced_to_set_backward_relation(self):
        _, branch1, actions = self._create_inforequest_scenario(u'advancement')
        _, (advancement, [(branch2, _)]) = actions
        result = advancement.advanced_to_set.all()
        self.assertItemsEqual(result, [branch2])

    def test_action_advanced_to_set_backward_relation_empty_by_default(self):
        _, branch, (request,) = self._create_inforequest_scenario()
        result = request.advanced_to_set.all()
        self.assertItemsEqual(result, [])

    def test_no_default_ordering(self):
        self.assertFalse(Branch.objects.all().ordered)

    def test_is_main_property(self):
        _, branch1, actions = self._create_inforequest_scenario(u'advancement')
        _, (_, [(branch2, _)]) = actions
        self.assertTrue(branch1.is_main)
        self.assertFalse(branch2.is_main)

    def test_prefetch_actions_staticmethod(self):
        inforequest, branch, actions = self._create_inforequest_scenario(u'confirmation', u'extension')

        # Without arguments
        with self.assertNumQueries(2):
            branch = Branch.objects.prefetch_related(Branch.prefetch_actions()).get(pk=branch.pk)
        with self.assertNumQueries(0):
            self.assertEqual(branch.actions, actions)

        # With custom path and queryset
        with self.assertNumQueries(3):
            inforequest = (Inforequest.objects
                    .prefetch_related(Inforequest.prefetch_branches())
                    .prefetch_related(Branch.prefetch_actions(u'branches', Action.objects.extra(select=dict(moo=47))))
                    .get(pk=inforequest.pk))
        with self.assertNumQueries(0):
            self.assertEqual(inforequest.branches[0].actions, actions)
            self.assertEqual(inforequest.branches[0].actions[0].moo, 47)

    def test_actions_property(self):
        _, branch, actions = self._create_inforequest_scenario(u'confirmation', u'extension')

        # Property is cached
        with self.assertNumQueries(1):
            branch = Branch.objects.get(pk=branch.pk)
        with self.assertNumQueries(1):
            self.assertEqual(branch.actions, actions)
        with self.assertNumQueries(0):
            self.assertEqual(branch.actions, actions)

        # Property is prefetched with prefetch_actions()
        with self.assertNumQueries(2):
            branch = Branch.objects.prefetch_related(Branch.prefetch_actions()).get(pk=branch.pk)
        with self.assertNumQueries(0):
            self.assertEqual(branch.actions, actions)

    def test_actions_property_with_no_actions(self):
        inforequest = self._create_inforequest()
        branch = self._create_branch(inforequest=inforequest)

        # Property is cached
        with self.assertNumQueries(1):
            branch = Branch.objects.get(pk=branch.pk)
        with self.assertNumQueries(1):
            self.assertEqual(branch.actions, [])
        with self.assertNumQueries(0):
            self.assertEqual(branch.actions, [])

        # Property is prefetched with prefetch_actions()
        with self.assertNumQueries(2):
            branch = Branch.objects.prefetch_related(Branch.prefetch_actions()).get(pk=branch.pk)
        with self.assertNumQueries(0):
            self.assertEqual(branch.actions, [])

    def test_prefetch_actions_by_email_staticmethod(self):
        inforequest, branch, actions = self._create_inforequest_scenario((u'confirmation', dict(email=False)), u'extension')
        request, confirmation, extension = actions

        # Without arguments
        with self.assertNumQueries(2):
            branch = Branch.objects.prefetch_related(Branch.prefetch_actions_by_email()).get(pk=branch.pk)
        with self.assertNumQueries(0):
            self.assertEqual(branch.actions_by_email, [request, extension])

        # With custom path and queryset
        with self.assertNumQueries(3):
            inforequest = (Inforequest.objects
                    .prefetch_related(Inforequest.prefetch_branches())
                    .prefetch_related(Branch.prefetch_actions_by_email(u'branches', Action.objects.extra(select=dict(moo=47))))
                    .get(pk=inforequest.pk))
        with self.assertNumQueries(0):
            self.assertEqual(inforequest.branches[0].actions_by_email, [request, extension])
            self.assertEqual(inforequest.branches[0].actions_by_email[0].moo, 47)

    def test_actions_by_email_property(self):
        _, branch, actions = self._create_inforequest_scenario((u'confirmation', dict(email=False)), u'extension')
        request, confirmation, extension = actions

        # Property is cached
        with self.assertNumQueries(1):
            branch = Branch.objects.get(pk=branch.pk)
        with self.assertNumQueries(1):
            self.assertEqual(branch.actions_by_email, [request, extension])

        # Property uses cached actions property
        with self.assertNumQueries(1):
            branch = Branch.objects.get(pk=branch.pk)
        with self.assertNumQueries(1):
            branch.actions
        with self.assertNumQueries(0):
            self.assertEqual(branch.actions_by_email, [request, extension])

        # Property is prefetched with prefetch_actions_by_email()
        with self.assertNumQueries(2):
            branch = Branch.objects.prefetch_related(Branch.prefetch_actions_by_email()).get(pk=branch.pk)
        with self.assertNumQueries(0):
            self.assertEqual(branch.actions_by_email, [request, extension])

        # Property is prefetched with prefetch_actions()
        with self.assertNumQueries(2):
            branch = Branch.objects.prefetch_related(Branch.prefetch_actions()).get(pk=branch.pk)
        with self.assertNumQueries(0):
            self.assertEqual(branch.actions_by_email, [request, extension])

    def test_prefetch_last_action_staticmethod(self):
        inforequest, branch, actions = self._create_inforequest_scenario(u'confirmation', u'extension')
        _, _, extension = actions

        # Without arguments
        with self.assertNumQueries(2):
            branch = Branch.objects.prefetch_related(Branch.prefetch_last_action()).get(pk=branch.pk)
        with self.assertNumQueries(0):
            self.assertEqual(branch._last_action, [extension])

        # With custom path and queryset
        with self.assertNumQueries(3):
            inforequest = (Inforequest.objects
                    .prefetch_related(Inforequest.prefetch_branches())
                    .prefetch_related(Branch.prefetch_last_action(u'branches', Action.objects.extra(select=dict(moo=47))))
                    .get(pk=inforequest.pk))
        with self.assertNumQueries(0):
            self.assertEqual(inforequest.branches[0]._last_action, [extension])
            self.assertEqual(inforequest.branches[0]._last_action[0].moo, 47)

    def test_last_action_property(self):
        _, branch, actions = self._create_inforequest_scenario(u'confirmation', u'extension')
        _, _, extension = actions

        # Property is cached
        with self.assertNumQueries(1):
            branch = Branch.objects.get(pk=branch.pk)
        with self.assertNumQueries(1):
            self.assertEqual(branch.last_action, extension)
        with self.assertNumQueries(0):
            self.assertEqual(branch.last_action, extension)

        # Property uses cached actions property
        with self.assertNumQueries(1):
            branch = Branch.objects.get(pk=branch.pk)
        with self.assertNumQueries(1):
            branch.actions
        with self.assertNumQueries(0):
            self.assertEqual(branch.last_action, extension)

        # Property is prefetched with prefetch_last_action()
        with self.assertNumQueries(2):
            branch = Branch.objects.prefetch_related(Branch.prefetch_last_action()).get(pk=branch.pk)
        with self.assertNumQueries(0):
            self.assertEqual(branch.last_action, extension)

        # Property is prefetched with prefetch_actions()
        with self.assertNumQueries(2):
            branch = Branch.objects.prefetch_related(Branch.prefetch_actions()).get(pk=branch.pk)
        with self.assertNumQueries(0):
            self.assertEqual(branch.last_action, extension)

    def test_last_action_property_with_no_actions(self):
        inforequest = self._create_inforequest()
        branch = self._create_branch(inforequest=inforequest)

        # Property is cached
        with self.assertNumQueries(1):
            branch = Branch.objects.get(pk=branch.pk)
        with self.assertNumQueries(1):
            self.assertIsNone(branch.last_action)
        with self.assertNumQueries(0):
            self.assertIsNone(branch.last_action)

        # Property uses cached actions property
        with self.assertNumQueries(1):
            branch = Branch.objects.get(pk=branch.pk)
        with self.assertNumQueries(1):
            branch.actions
        with self.assertNumQueries(0):
            self.assertIsNone(branch.last_action)

        # Property is prefetched with prefetch_last_action()
        with self.assertNumQueries(2):
            branch = Branch.objects.prefetch_related(Branch.prefetch_last_action()).get(pk=branch.pk)
        with self.assertNumQueries(0):
            self.assertIsNone(branch.last_action)

        # Property is prefetched with prefetch_actions()
        with self.assertNumQueries(2):
            branch = Branch.objects.prefetch_related(Branch.prefetch_actions()).get(pk=branch.pk)
        with self.assertNumQueries(0):
            self.assertIsNone(branch.last_action)

    def test_can_add_x_properties(self):
        tests = (
                (Action.TYPES.REQUEST, Bunch(
                    scenario=[],
                    allowed=[           u'confirmation', u'extension', u'advancement', u'clarification_request', u'disclosure', u'refusal', u'obligee_action', u'obligee_email_action'],
                    expired=[u'appeal', u'confirmation', u'extension', u'advancement', u'clarification_request', u'disclosure', u'refusal', u'obligee_action', u'obligee_email_action', u'applicant_action'],
                    )),
                (Action.TYPES.CLARIFICATION_RESPONSE, Bunch(
                    scenario=[u'clarification_request', u'clarification_response'],
                    allowed=[           u'extension', u'advancement', u'clarification_request', u'disclosure', u'refusal', u'obligee_action', u'obligee_email_action'],
                    expired=[u'appeal', u'extension', u'advancement', u'clarification_request', u'disclosure', u'refusal', u'obligee_action', u'obligee_email_action', u'applicant_action'],
                    )),
                (Action.TYPES.APPEAL, Bunch(
                    scenario=[u'expiration', u'appeal'],
                    allowed=[u'affirmation', u'reversion', u'remandment', u'obligee_action'],
                    expired=[u'affirmation', u'reversion', u'remandment', u'obligee_action'],
                    )),
                (Action.TYPES.CONFIRMATION, Bunch(
                    scenario=[u'confirmation'],
                    allowed=[           u'extension', u'advancement', u'clarification_request', u'disclosure', u'refusal', u'obligee_action', u'obligee_email_action'],
                    expired=[u'appeal', u'extension', u'advancement', u'clarification_request', u'disclosure', u'refusal', u'obligee_action', u'obligee_email_action', u'applicant_action'],
                    )),
                (Action.TYPES.EXTENSION, Bunch(
                    scenario=[u'extension'],
                    allowed=[           u'disclosure', u'refusal', u'obligee_action', u'obligee_email_action'],
                    expired=[u'appeal', u'disclosure', u'refusal', u'obligee_action', u'obligee_email_action', u'applicant_action'],
                    )),
                (Action.TYPES.ADVANCEMENT, Bunch(
                    scenario=[u'advancement'],
                    allowed=[u'appeal', u'applicant_action'],
                    expired=[u'appeal', u'applicant_action'],
                    )),
                (Action.TYPES.CLARIFICATION_REQUEST, Bunch(
                    scenario=[u'clarification_request'],
                    allowed=[u'clarification_response', u'clarification_request', u'obligee_action', u'obligee_email_action', u'applicant_action', u'applicant_email_action'],
                    expired=[u'clarification_response', u'clarification_request', u'obligee_action', u'obligee_email_action', u'applicant_action', u'applicant_email_action'],
                    )),
                (Action.TYPES.DISCLOSURE, Bunch(
                    scenario=[(u'disclosure', dict(disclosure_level=Action.DISCLOSURE_LEVELS.NONE))],
                    allowed=[u'appeal', u'applicant_action'],
                    expired=[u'appeal', u'applicant_action'],
                    )),
                (Action.TYPES.DISCLOSURE, Bunch(
                    scenario=[(u'disclosure', dict(disclosure_level=Action.DISCLOSURE_LEVELS.PARTIAL))],
                    allowed=[u'appeal', u'applicant_action'],
                    expired=[u'appeal', u'applicant_action'],
                    )),
                (Action.TYPES.DISCLOSURE, Bunch(
                    scenario=[(u'disclosure', dict(disclosure_level=Action.DISCLOSURE_LEVELS.FULL))],
                    allowed=[],
                    expired=[],
                    )),
                (Action.TYPES.REFUSAL, Bunch(
                    scenario=[u'refusal'],
                    allowed=[u'appeal', u'applicant_action'],
                    expired=[u'appeal', u'applicant_action'],
                    )),
                (Action.TYPES.AFFIRMATION, Bunch(
                    scenario=[u'refusal', u'appeal', u'affirmation'],
                    allowed=[],
                    expired=[],
                    )),
                (Action.TYPES.REVERSION, Bunch(
                    scenario=[u'refusal', u'appeal', u'reversion'],
                    allowed=[],
                    expired=[],
                    )),
                (Action.TYPES.REMANDMENT, Bunch(
                    scenario=[u'refusal', u'appeal', u'remandment'],
                    allowed=[           u'extension', u'disclosure', u'refusal', u'obligee_action', u'obligee_email_action'],
                    expired=[u'appeal', u'extension', u'disclosure', u'refusal', u'obligee_action', u'obligee_email_action', u'applicant_action'],
                    )),
                (Action.TYPES.ADVANCED_REQUEST, Bunch(
                    branch=1,
                    scenario=[u'advancement'],
                    allowed=[           u'confirmation', u'extension', u'advancement', u'clarification_request', u'disclosure', u'refusal', u'obligee_action', u'obligee_email_action'],
                    expired=[u'appeal', u'confirmation', u'extension', u'advancement', u'clarification_request', u'disclosure', u'refusal', u'obligee_action', u'obligee_email_action', u'applicant_action'],
                    )),
                (Action.TYPES.EXPIRATION, Bunch(
                    scenario=[u'expiration'],
                    allowed=[u'appeal', u'applicant_action'],
                    expired=[u'appeal', u'applicant_action'],
                    )),
                (Action.TYPES.APPEAL_EXPIRATION, Bunch(
                    scenario=[u'refusal', u'appeal', u'appeal_expiration'],
                    allowed=[],
                    expired=[],
                    )),
                )
        # Make sure we are testing all defined action types
        tested_action_types = set(a for a, _ in tests)
        defined_action_types = Action.TYPES._inverse.keys()
        self.assertItemsEqual(tested_action_types, defined_action_types)

        can_add_properties = (
                u'request',
                u'clarification_response',
                u'appeal',
                u'confirmation',
                u'extension',
                u'advancement',
                u'clarification_request',
                u'disclosure',
                u'refusal',
                u'affirmation',
                u'reversion',
                u'remandment',
                u'applicant_action',
                u'applicant_email_action',
                u'obligee_action',
                u'obligee_email_action',
                )

        for action_type, test in tests:
            timewarp.jump(local_datetime_from_local(u'2010-07-05 10:33:00'))
            objs = self._create_inforequest_scenario(*test.scenario)
            branch = getattr(test, u'branch', 0)
            branch = [o for o in flatten(objs) if isinstance(o, Branch)][branch]
            self.assertEqual(branch.last_action.type, action_type)

            # Check actions allowed when the last action deadline is not expired yet
            for can_add_property in can_add_properties:
                value = getattr(branch, u'can_add_%s' % can_add_property)
                expected = can_add_property in test.allowed
                self.assertEqual(value, expected, u'can_add_%s is %s after %r' % (can_add_property, value, test.scenario))

            # Check actions allowed when the last action deadline is expired
            timewarp.jump(local_datetime_from_local(u'2010-10-05 10:33:00'))
            branch = Branch.objects.get(pk=branch.pk)
            for can_add_property in can_add_properties:
                value = getattr(branch, u'can_add_%s' % can_add_property)
                expected = can_add_property in test.expired
                self.assertEqual(value, expected, u'can_add_%s is %s after expired %r' % (can_add_property, value, test.scenario))

    def test_can_add_action_method(self):
        tests = (                                   # expected result
                (Action.TYPES.REQUEST,                False,          None),
                (Action.TYPES.CLARIFICATION_RESPONSE, False,          None),
                (Action.TYPES.APPEAL,                 False,          None),
                (Action.TYPES.CONFIRMATION,           True,           None),
                (Action.TYPES.EXTENSION,              True,           None),
                (Action.TYPES.ADVANCEMENT,            True,           None),
                (Action.TYPES.CLARIFICATION_REQUEST,  True,           None),
                (Action.TYPES.DISCLOSURE,             True,           None),
                (Action.TYPES.REFUSAL,                True,           None),
                (Action.TYPES.AFFIRMATION,            False,          None),
                (Action.TYPES.REVERSION,              False,          None),
                (Action.TYPES.REMANDMENT,             False,          None),
                (Action.TYPES.ADVANCED_REQUEST,       AttributeError, u"'Branch' object has no attribute 'can_add_advanced_request'"),
                (Action.TYPES.EXPIRATION,             AttributeError, u"'Branch' object has no attribute 'can_add_expiration'"),
                (Action.TYPES.APPEAL_EXPIRATION,      AttributeError, u"'Branch' object has no attribute 'can_add_appeal_expiration'"),
                )
        # Make sure we are testing all defined action types
        tested_action_types = set(a for a, _, _ in tests)
        defined_action_types = Action.TYPES._inverse.keys()
        self.assertItemsEqual(tested_action_types, defined_action_types)

        # ``branch`` last action is ``REQUEST``
        _, branch, _ = self._create_inforequest_scenario()
        for action_type, expected_result, expected_message in tests:
            if expected_result is True:
                self.assertTrue(branch.can_add_action(action_type))
            elif expected_result is False:
                self.assertFalse(branch.can_add_action(action_type))
            else:
                with self.assertRaisesMessage(expected_result, expected_message):
                    branch.can_add_action(action_type)

    def test_can_add_action_method_with_multiple_arguments(self):
        tests = (
                ([Action.TYPES.REQUEST,      Action.TYPES.APPEAL,     Action.TYPES.REVERSION], False,          None),
                ([Action.TYPES.CONFIRMATION, Action.TYPES.EXTENSION],                          True,           None),
                ([Action.TYPES.APPEAL,       Action.TYPES.EXTENSION,  Action.TYPES.REVERSION], True,           None),
                ([Action.TYPES.AFFIRMATION,  Action.TYPES.EXPIRATION, Action.TYPES.EXTENSION], AttributeError, u"'Branch' object has no attribute 'can_add_expiration'"),
                ([],                                                                           False,          None),
                )

        # ``branch`` last action is ``REQUEST``
        _, branch, _ = self._create_inforequest_scenario()
        for action_types, expected_result, expected_message in tests:
            if expected_result is True:
                self.assertTrue(branch.can_add_action(*action_types), u'can_add_action(%s) is False' % action_types)
            elif expected_result is False:
                self.assertFalse(branch.can_add_action(*action_types), u'can_add_action(%s) is True' % action_types)
            else:
                with self.assertRaisesMessage(expected_result, expected_message):
                    branch.can_add_action(*action_types)

    def test_add_expiration_if_expired_method(self):
        tests = (                                   # Expected action type,      branch, scenario
                (Action.TYPES.REQUEST,                Action.TYPES.EXPIRATION,        0, []),
                (Action.TYPES.CLARIFICATION_RESPONSE, Action.TYPES.EXPIRATION,        0, [u'clarification_request', u'clarification_response']),
                (Action.TYPES.APPEAL,                 Action.TYPES.APPEAL_EXPIRATION, 0, [u'expiration', u'appeal']),
                (Action.TYPES.CONFIRMATION,           Action.TYPES.EXPIRATION,        0, [u'confirmation']),
                (Action.TYPES.EXTENSION,              Action.TYPES.EXPIRATION,        0, [u'extension']),
                (Action.TYPES.ADVANCEMENT,            None,                           0, [u'advancement']),
                (Action.TYPES.CLARIFICATION_REQUEST,  None,                           0, [u'clarification_request']),
                (Action.TYPES.DISCLOSURE,             None,                           0, [u'disclosure']),
                (Action.TYPES.REFUSAL,                None,                           0, [u'refusal']),
                (Action.TYPES.AFFIRMATION,            None,                           0, [u'refusal', u'appeal', u'affirmation']),
                (Action.TYPES.REVERSION,              None,                           0, [u'refusal', u'appeal', u'reversion']),
                (Action.TYPES.REMANDMENT,             Action.TYPES.EXPIRATION,        0, [u'refusal', u'appeal', u'remandment']),
                (Action.TYPES.ADVANCED_REQUEST,       Action.TYPES.EXPIRATION,        1, [u'advancement']),
                (Action.TYPES.EXPIRATION,             None,                           0, [u'expiration']),
                (Action.TYPES.APPEAL_EXPIRATION,      None,                           0, [u'refusal', u'appeal', u'appeal_expiration']),
                )
        # Make sure we are testing all defined action types
        tested_action_types = set(a for a, _, _, _ in tests)
        defined_action_types = Action.TYPES._inverse.keys()
        self.assertItemsEqual(tested_action_types, defined_action_types)

        for action_type, expected_action_type, branch, scenario in tests:
            timewarp.jump(local_datetime_from_local(u'2010-07-05 10:33:00'))
            objs = self._create_inforequest_scenario(*scenario)
            branch = [o for o in flatten(objs) if isinstance(o, Branch)][branch]
            self.assertEqual(branch.last_action.type, action_type)
            original_last_action = branch.last_action

            # Deadline not expired yet
            with created_instances(Action.objects) as action_set:
                branch.add_expiration_if_expired()
            self.assertEqual(action_set.count(), 0)

            # Any deadline is expired now
            timewarp.jump(local_datetime_from_local(u'2010-10-05 10:33:00'))
            branch = Branch.objects.get(pk=branch.pk)
            with created_instances(Action.objects) as action_set:
                branch.add_expiration_if_expired()

            branch = Branch.objects.get(pk=branch.pk)
            if expected_action_type is None:
                self.assertEqual(action_set.count(), 0)
                self.assertEqual(branch.last_action, original_last_action)
            else:
                added_action = action_set.get()
                self.assertEqual(branch.last_action, added_action)
                self.assertEqual(added_action.type, expected_action_type)
                self.assertEqual(added_action.effective_date, naive_date(u'2010-10-05'))

    def test_collect_obligee_emails_method(self):
        obligee = self._create_obligee(emails=u'Obligee1 <oblige1@a.com>, oblige2@a.com')
        _, branch, _ = self._create_inforequest_scenario(obligee,
                (u'request', dict(
                    email=dict(from_name=u'Request From', from_mail=u'request-from@a.com'),
                    recipients=[
                        dict(name=u'Request To1', mail=u'request-to1@a.com', type=Recipient.TYPES.TO),
                        dict(name=u'Request To2', mail=u'request-to2@a.com', type=Recipient.TYPES.TO),
                        dict(name=u'Request Cc', mail=u'request-cc@a.com', type=Recipient.TYPES.CC),
                        dict(name=u'Request Bcc', mail=u'request-bcc@a.com', type=Recipient.TYPES.BCC),
                        ],
                    )),
                (u'refusal', dict(
                    email=dict(from_name=u'Refusal From', from_mail=u'refusal-from@a.com'),
                    recipients=[
                        dict(name=u'Refusal To', mail=u'refusal-to@a.com', type=Recipient.TYPES.TO),
                        dict(name=u'Refusal Cc', mail=u'refusal-cc@a.com', type=Recipient.TYPES.CC),
                        dict(name=u'Refusal Bcc', mail=u'refusal-bcc@a.com', type=Recipient.TYPES.BCC),
                        ],
                    )),
                )

        result = branch.collect_obligee_emails()
        self.assertItemsEqual(result, [
                # Outboud email contributes with its recipient addresses only
                (u'Request To1',  u'request-to1@a.com'),
                (u'Request To2',  u'request-to2@a.com'),
                (u'Request Cc',   u'request-cc@a.com'),
                (u'Request Bcc',  u'request-bcc@a.com'),
                # Inbound email contributes with its from address only
                (u'Refusal From', u'refusal-from@a.com'),
                # Currect obligee addresses
                (u'Obligee1',     u'oblige1@a.com'),
                (u'',             u'oblige2@a.com'),
                ])

    def test_collect_obligee_emails_method_gives_priority_to_more_recent_messages(self):
        u"""
        Checks that if the same email address is used in multiple messages with different names,
        the name used with the most recent message has priority.
        """
        obligee = self._create_obligee(emails=u'Obligee <oblige@a.com>')
        _, branch, _ = self._create_inforequest_scenario(obligee,
                (u'request', dict(recipients=[dict(name=u'Request To', mail=u'address@a.com', type=Recipient.TYPES.TO)])),
                (u'refusal', dict(email=dict(from_name=u'Refusal From', from_mail=u'address@a.com'))),
                )

        result = branch.collect_obligee_emails()
        self.assertItemsEqual(result, [
                # Address name from later email has priority
                (u'Refusal From', u'address@a.com'),
                # Obligee instance address
                (u'Obligee',      u'oblige@a.com'),
                ])

    def test_collect_obligee_emails_method_gives_priority_to_obligee_instance(self):
        u"""
        Checks that if the same email address is used as obligee address and inbound message from
        adress with different names, the name used with obligee instance has priority.
        """
        obligee = self._create_obligee(emails=u'Obligee <address@a.com>')
        _, branch, _ = self._create_inforequest_scenario(obligee,
                (u'request', dict(recipients=[dict(name=u'Request To', mail=u'address@a.com', type=Recipient.TYPES.TO)])),
                (u'refusal', dict(email=dict(from_name=u'Refusal From', from_mail=u'address@a.com'))),
                )

        result = branch.collect_obligee_emails()
        self.assertItemsEqual(result, [
                # Obligee instance address has priority
                (u'Obligee', u'address@a.com'),
                ])

    def test_collect_obligee_emails_method_ignores_addresses_from_other_branches(self):
        obligee1 = self._create_obligee(emails=u'Obligee1 <obligee1@a.com>')
        obligee2 = self._create_obligee(emails=u'Ignored <obligee2@a.com>')
        _, branch, actions = self._create_inforequest_scenario(obligee1,
                u'request',
                u'refusal',
                (u'advancement', [obligee2, u'advanced_request', u'refusal']),
                )
        result = list(branch.collect_obligee_emails())
        self.assertItemsEqual(result, [(u'Obligee1', u'obligee1@a.com')])

        # For reference check that the method for the advanced branch returs the other address
        branch2 = [o for o in flatten(actions) if isinstance(o, Branch)][0]
        result = list(branch2.collect_obligee_emails())
        self.assertItemsEqual(result, [(u'Ignored', u'obligee2@a.com')])

    def test_repr(self):
        _, branch, _ = self._create_inforequest_scenario()
        self.assertEqual(repr(branch), u'<Branch: %s>' % branch.pk)

    def test_main_and_advanced_query_methods(self):
        _, branch1, actions = self._create_inforequest_scenario((u'advancement', [], []))
        _, (_, [(branch2, _), (branch3, _)]) = actions
        result = Branch.objects.main()
        self.assertItemsEqual(result, [branch1])
        result = Branch.objects.advanced()
        self.assertItemsEqual(result, [branch2, branch3])

    def test_order_by_pk_query_method(self):
        inforequest = self._create_inforequest()
        branches = [self._create_branch(inforequest=inforequest) for i in range(20)]
        sample = random.sample(branches, 10)
        result = Branch.objects.filter(pk__in=(d.pk for d in sample)).order_by_pk().reverse()
        self.assertEqual(list(result), sorted(sample, key=lambda d: -d.pk))
