# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

__author__ = "Microsoft Corporation <ptvshelp@microsoft.com>"
__version__ = "4.0.0a3"

import sys


# Py3 compat - alias unicode to str, and xrange to range
try:
    unicode  # noqa
except NameError:
    unicode = str
try:
    xrange  # noqa
except NameError:
    xrange = range


class SafeRepr(object):
    # String types are truncated to maxstring_outer when at the outer-
    # most level, and truncated to maxstring_inner characters inside
    # collections.
    maxstring_outer = 2 ** 16
    maxstring_inner = 30
    if sys.version_info >= (3, 0):
        string_types = (str, bytes)
        set_info = (set, '{', '}', False)
        frozenset_info = (frozenset, 'frozenset({', '})', False)
        int_types = (int,)
    else:
        string_types = (str, unicode)
        set_info = (set, 'set([', '])', False)
        frozenset_info = (frozenset, 'frozenset([', '])', False)
        int_types = (int, long)  # noqa

    # Collection types are recursively iterated for each limit in
    # maxcollection.
    maxcollection = (15, 10)

    # Specifies type, prefix string, suffix string, and whether to include a
    # comma if there is only one element. (Using a sequence rather than a
    # mapping because we use isinstance() to determine the matching type.)
    collection_types = [
        (tuple, '(', ')', True),
        (list, '[', ']', False),
        frozenset_info,
        set_info,
    ]
    try:
        from collections import deque
        collection_types.append((deque, 'deque([', '])', False))
    except Exception:
        pass

    # type, prefix string, suffix string, item prefix string,
    # item key/value separator, item suffix string
    dict_types = [(dict, '{', '}', '', ': ', '')]
    try:
        from collections import OrderedDict
        dict_types.append((OrderedDict, 'OrderedDict([', '])', '(', ', ', ')'))
    except Exception:
        pass

    # All other types are treated identically to strings, but using
    # different limits.
    maxother_outer = 2 ** 16
    maxother_inner = 30

    def __call__(self, obj, convert_to_hex=False):
        try:
            return ''.join(self._repr(obj, 0, convert_to_hex=convert_to_hex))
        except Exception:
            try:
                return 'An exception was raised: %r' % sys.exc_info()[1]
            except Exception:
                return 'An exception was raised'

    def _repr(self, obj, level, convert_to_hex=False):
        '''Returns an iterable of the parts in the final repr string.'''

        try:
            obj_repr = type(obj).__repr__
        except Exception:
            obj_repr = None

        def has_obj_repr(t):
            r = t.__repr__
            try:
                return obj_repr == r
            except Exception:
                return obj_repr is r

        for t, prefix, suffix, comma in self.collection_types:
            if isinstance(obj, t) and has_obj_repr(t):
                return self._repr_iter(obj, level, prefix, suffix, comma,
                                       convert_to_hex=convert_to_hex)

        for t, prefix, suffix, item_prefix, item_sep, item_suffix in self.dict_types:  # noqa
            if isinstance(obj, t) and has_obj_repr(t):
                return self._repr_dict(obj, level, prefix, suffix,
                                       item_prefix, item_sep, item_suffix,
                                       convert_to_hex=convert_to_hex)

        for t in self.string_types:
            if isinstance(obj, t) and has_obj_repr(t):
                return self._repr_str(obj, level,
                                      convert_to_hex=convert_to_hex)

        if self._is_long_iter(obj):
            return self._repr_long_iter(obj, convert_to_hex=convert_to_hex)

        return self._repr_other(obj, level, convert_to_hex=convert_to_hex)

    # Determines whether an iterable exceeds the limits set in
    # maxlimits, and is therefore unsafe to repr().
    def _is_long_iter(self, obj, level=0):
        try:
            # Strings have their own limits (and do not nest). Because
            # they don't have __iter__ in 2.x, this check goes before
            # the next one.
            if isinstance(obj, self.string_types):
                return len(obj) > self.maxstring_inner

            # If it's not an iterable (and not a string), it's fine.
            if not hasattr(obj, '__iter__'):
                return False

            # Iterable is its own iterator - this is a one-off iterable
            # like generator or enumerate(). We can't really count that,
            # but repr() for these should not include any elements anyway,
            # so we can treat it the same as non-iterables.
            if obj is iter(obj):
                return False

            # xrange reprs fine regardless of length.
            if isinstance(obj, xrange):
                return False

            # numpy and scipy collections (ndarray etc) have
            # self-truncating repr, so they're always safe.
            try:
                module = type(obj).__module__.partition('.')[0]
                if module in ('numpy', 'scipy'):
                    return False
            except Exception:
                pass

            # Iterables that nest too deep are considered long.
            if level >= len(self.maxcollection):
                return True

            # It is too long if the length exceeds the limit, or any
            # of its elements are long iterables.
            if hasattr(obj, '__len__'):
                try:
                    size = len(obj)
                except Exception:
                    size = None
                if size is not None and size > self.maxcollection[level]:
                    return True
                return any((self._is_long_iter(item, level + 1) for item in obj))  # noqa
            return any(i > self.maxcollection[level] or self._is_long_iter(item, level + 1) for i, item in enumerate(obj))  # noqa

        except Exception:
            # If anything breaks, assume the worst case.
            return True

    def _repr_iter(self, obj, level, prefix, suffix,
                   comma_after_single_element=False, convert_to_hex=False):
        yield prefix

        if level >= len(self.maxcollection):
            yield '...'
        else:
            count = self.maxcollection[level]
            yield_comma = False
            for item in obj:
                if yield_comma:
                    yield ', '
                yield_comma = True

                count -= 1
                if count <= 0:
                    yield '...'
                    break

                for p in self._repr(item, 100 if item is obj else level + 1, convert_to_hex=convert_to_hex):  # noqa
                    yield p
            else:
                if comma_after_single_element:
                    if count == self.maxcollection[level] - 1:
                        yield ','
        yield suffix

    def _repr_long_iter(self, obj, convert_to_hex=False):
        try:
            length = hex(len(obj)) if convert_to_hex else len(obj)
            obj_repr = '<%s, len() = %s>' % (type(obj).__name__, length)
        except Exception:
            try:
                obj_repr = '<' + type(obj).__name__ + '>'
            except Exception:
                obj_repr = '<no repr available for object>'
        yield obj_repr

    def _repr_dict(self, obj, level, prefix, suffix,
                   item_prefix, item_sep, item_suffix, convert_to_hex=False):
        if not obj:
            yield prefix + suffix
            return
        if level >= len(self.maxcollection):
            yield prefix + '...' + suffix
            return

        yield prefix

        count = self.maxcollection[level]
        yield_comma = False

        try:
            sorted_keys = sorted(obj)
        except Exception:
            sorted_keys = list(obj)

        for key in sorted_keys:
            if yield_comma:
                yield ', '
            yield_comma = True

            count -= 1
            if count <= 0:
                yield '...'
                break

            yield item_prefix
            for p in self._repr(key, level + 1, convert_to_hex=convert_to_hex):
                yield p

            yield item_sep

            try:
                item = obj[key]
            except Exception:
                yield '<?>'
            else:
                for p in self._repr(item, 100 if item is obj else level + 1, convert_to_hex=convert_to_hex):  # noqa
                    yield p
            yield item_suffix

        yield suffix

    def _repr_str(self, obj, level, convert_to_hex=False):
        return self._repr_obj(obj, level,
                              self.maxstring_inner, self.maxstring_outer,
                              convert_to_hex=convert_to_hex)

    def _repr_other(self, obj, level, convert_to_hex=False):
        return self._repr_obj(obj, level,
                              self.maxother_inner, self.maxother_outer,
                              convert_to_hex=convert_to_hex)

    def _repr_obj(self, obj, level, limit_inner, limit_outer,
                  convert_to_hex=False):
        try:
            if isinstance(obj, self.int_types) and convert_to_hex:
                obj_repr = hex(obj)
            else:
                obj_repr = repr(obj)
        except Exception:
            try:
                obj_repr = object.__repr__(obj)
            except Exception:
                try:
                    obj_repr = '<no repr available for ' + type(obj).__name__ + '>'  # noqa
                except Exception:
                    obj_repr = '<no repr available for object>'

        limit = limit_inner if level > 0 else limit_outer

        if limit >= len(obj_repr):
            yield obj_repr
            return

        # Slightly imprecise calculations - we may end up with a string that is
        # up to 3 characters longer than limit. If you need precise formatting,
        # you are using the wrong class.
        left_count, right_count = max(1, int(2 * limit / 3)), max(1, int(limit / 3))  # noqa

        yield obj_repr[:left_count]
        yield '...'
        yield obj_repr[-right_count:]
