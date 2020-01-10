# -*- coding: utf-8 -*-
#
# Copyright 2007-2010 Fedora Unity Project (http://fedoraunity.org)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from revisor.constants import domain
import gettext
import os

N_ = lambda x: x
_ = lambda x: gettext.ldgettext(domain, x)

def getDefaultLangs():
    languages = []
    for envar in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
        val = os.environ.get(envar)
        if val:
            languages = val.split(':')
            break
    if 'C' not in languages:
        languages.append('C')

    # now normalize and expand the languages
    nelangs = []
    for lang in languages:
        for nelang in gettext._expand_lang(lang):
            if nelang not in nelangs:
                nelangs.append(nelang)
    return nelangs  
