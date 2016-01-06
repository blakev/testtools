# Copyright (c) testtools developers. See LICENSE for details.

"""Tests for Deferred matchers."""

from extras import try_import

from testtools.compat import _u
from testtools.content import TracebackContent
from testtools._deferredmatchers import (
    no_result,
    successful,
)
from testtools.matchers import (
    AfterPreprocessing,
    Equals,
    Is,
    MatchesDict,
)
from testtools.tests.test_spinner import NeedsTwistedTestCase


defer = try_import('twisted.internet.defer')
failure = try_import('twisted.python.failure')


def mismatches(description, details=None):
    """Match a ``Mismatch`` object."""
    if details is None:
        details = Equals({})

    matcher = MatchesDict({
        'description': description,
        'details': details,
    })

    def get_mismatch_info(mismatch):
        return {
            'description': mismatch.describe(),
            'details': mismatch.get_details(),
        }

    return AfterPreprocessing(get_mismatch_info, matcher)


def make_failure(exc_value):
    """Raise ``exc_value`` and return the failure."""
    try:
        raise exc_value
    except:
        return failure.Failure()


class NoResultTests(NeedsTwistedTestCase):
    """Tests for ``no_result``."""

    def match(self, thing):
        return no_result().match(thing)

    def test_unfired_matches(self):
        # A Deferred that hasn't fired matches no_result.
        self.assertThat(self.match(defer.Deferred()), Is(None))

    def test_successful_does_no_match(self):
        # A Deferred that's fired successfully does not match no_result.
        result = object()
        deferred = defer.succeed(result)
        mismatch = self.match(deferred)
        self.assertThat(
            mismatch, mismatches(Equals(_u(
                '%r has already fired with %r' % (deferred, result)))))

    def test_failed_does_not_match(self):
        # A Deferred that's failed does not match no_result.
        fail = make_failure(RuntimeError('arbitrary failure'))
        deferred = defer.fail(fail)
        # Suppress unhandled error in Deferred.
        self.addCleanup(deferred.addErrback, lambda _: None)
        mismatch = self.match(deferred)
        self.assertThat(
            mismatch, mismatches(Equals(_u(
                '%r has already fired with %r' % (deferred, fail)))))

    def test_success_after_assertion(self):
        # We can create a Deferred, assert that it hasn't fired, then fire it
        # and collect the result.
        deferred = defer.Deferred()
        self.assertThat(deferred, no_result())
        results = []
        deferred.addCallback(results.append)
        marker = object()
        deferred.callback(marker)
        self.assertThat(results, Equals([marker]))

    def test_failure_after_assertion(self):
        # We can create a Deferred, assert that it hasn't fired, then fire it
        # with a failure and collect the result.
        deferred = defer.Deferred()
        self.assertThat(deferred, no_result())
        results = []
        deferred.addErrback(results.append)
        fail = make_failure(RuntimeError('arbitrary failure'))
        deferred.errback(fail)
        self.assertThat(results, Equals([fail]))


class SuccessResultTests(NeedsTwistedTestCase):

    def match(self, matcher, value):
        return successful(matcher).match(value)

    def test_successful_result_passes(self):
        # A Deferred that has fired successfully matches against the value it
        # was fired with.
        result = object()
        deferred = defer.succeed(result)
        self.assertThat(self.match(Is(result), deferred), Is(None))

    def test_different_successful_result_fails(self):
        # A Deferred that has fired successfully matches against the value it
        # was fired with.
        result = object()
        deferred = defer.succeed(result)
        matcher = Is(None)  # Something that doesn't match `result`.
        mismatch = matcher.match(result)
        self.assertThat(
            self.match(matcher, deferred),
            mismatches(Equals(mismatch.describe()),
                       Equals(mismatch.get_details())))

    def test_not_fired_fails(self):
        # A Deferred that has not yet fired fails to match.
        deferred = defer.Deferred()
        arbitrary_matcher = Is(None)
        self.assertThat(
            self.match(arbitrary_matcher, deferred),
            mismatches(Equals(_u('%r has not fired') % (deferred,))))

    def test_failing_fails(self):
        # A Deferred that has fired with a failure fails to match.
        deferred = defer.Deferred()
        fail = make_failure(RuntimeError('arbitrary failure'))
        deferred.errback(fail)
        arbitrary_matcher = Is(None)
        self.assertThat(
            self.match(arbitrary_matcher, deferred),
            mismatches(
                Equals(u'Success result expected on %r, found failure result '
                       u'instead: %r' % (deferred, fail)),
                Equals({'traceback': TracebackContent(
                    (fail.type, fail.value, fail.getTracebackObject()), None,
                )}),
            ))


def test_suite():
    from unittest2 import TestLoader, TestSuite
    return TestLoader().loadTestsFromName(__name__)
