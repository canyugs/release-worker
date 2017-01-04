# -*- coding: utf-8 -*-
import re
import gitlab
import ConfigParser
import sys
import os


class ReleaseWorker:

    def __init__(self, gitlab_url, personal_access_tokens):
        # auth
        self.personal_access_tokens = personal_access_tokens
        self.url = gitlab_url
        self.gl = gitlab.Gitlab(self.url, self.personal_access_tokens)
        self.gl.auth()

        # store
        self.project_obj = None  # project object
        self.branchs_obj = None  # store all branch
        self.project_id = None
        self.project_name = None
        self.tags = None  # project's tags
        self.latest_date = None
        self.latest_tag = None
        self.latest_tag_obj = None  # tag object
        self.latest_tag_commit_obj = None  # commit object in tag
        self._merge_requests = []  # Store merge request
        self._general_commits = []  # Store commits
        self._feature_commits = []
        self._bugfix_commits = []
        self._other_commits = []
        self.release_name = None
        self.release_branch = 'master'  # default branch is master
        self.full_link = True
        self.detail = True

    def headers(self):
        return self.gl.headers['PRIVATE-TOKEN']

    def search(self, string):
        return self.gl.projects.search(string)

    def get_id(self, project_name):
        lst = self.search(project_name)
        for idx in range(len(lst)):
            if lst[idx].name == project_name:
                self.project_obj = lst[idx]
                self.project_id = lst[idx].id
                self.project_name = lst[idx].name
                return lst[idx].id
        print 'project not found: %s' % project_name

    def get_project(self, project_name):
        self.get_id(project_name)
        return self.project_obj

    def get_name_dict(self, object_lst):
        """
        Show Obj's name is dict format, but object should has name property.
        return example with tag object:
        {u'release/2.2.2.1820': <gitlab.objects.ProjectTag at 0x108c35910>,
         u'release/2.2.2.1845': <gitlab.objects.ProjectTag at 0x108c35810>,}
        """
        tmp_dict = {}
        for _ in object_lst:
            tmp_dict[_.name] = _
        return tmp_dict

    def get_project_tags(self):
        """
        return example:
        [<gitlab.objects.ProjectTag at 0x103a95ad0>,
         <gitlab.objects.ProjectTag at 0x103a95b10>,
         <gitlab.objects.ProjectTag at 0x103a95b90>,
         <gitlab.objects.ProjectTag at 0x103a95c90>,
        """
        lst = self.project_obj.tags.list()
        return lst

    def get_tag_detail(self, tag_obj, option):
        """
        option example:

        {u'commit': <gitlab.objects.ProjectCommit at 0x103a95b50>,
         'gitlab': <gitlab.Gitlab at 0x103162750>,
         'id': None,
         u'message': u'v2.0.2.0003',
         u'name': u'v2.0.2.0003',
         'project_id': 131,
         u'release': None}
        """
        return tag_obj.as_dict()[option]

    def get_tag_commit_detail(self, commit_obj_in_tag, option):
        """
        option example:

        {u'author_email': u'jiahong.wu@hopebaytech.com',
         u'author_name': u'Jiahong',
         u'authored_date': u'2015-10-06T17:08:44.000+08:00',
         u'committed_date': u'2015-10-06T17:08:44.000+08:00',
         u'committer_email': u'jiahong.wu@hopebaytech.com',
         u'committer_name': u'Jiahong',
         'gitlab': <gitlab.Gitlab at 0x103162750>,
         u'id': u'e53b2958650248ce048f9216500af00216e5b631',
         u'message': u" Merge branch 'dev' into 'release'\n\nRelease 2.0.2.0003\n",
         u'parent_ids': [u'00b3471c6721e60ae9f1374551dafe080f1a4f6d',
         u'1a56a0c1bbd9378e5def594d0fcd5a3412b5ef5d']}
        """
        return commit_obj_in_tag.as_dict()[option]

    def get_tag_by_name(self, tag_name):
        lst = self.get_project_tags()
        tag_dict = self.get_name_dict(lst)
        return tag_dict[tag_name]

    def get_latest_tag(self):
        tmp_dict = {}
        lst = self.get_project_tags()
        for tag in lst:
            commit = self.get_tag_detail(tag, u'commit')
            date = self.get_tag_commit_detail(commit, u'committed_date')
            tmp_dict[date] = {'tag_name': tag.name,
                              'tag_obj': tag,
                              'tag_commit_obj': commit}
        # Sort by date
        tmp_key_list_sorted = sorted(tmp_dict.keys())
        latest_date = tmp_key_list_sorted[-1]
        latest_tag = tmp_dict[latest_date]['tag_name']

        self.latest_date = latest_date
        self.latest_tag = latest_tag
        self.latest_tag_obj = tmp_dict[latest_date]['tag_obj']
        self.latest_tag_commit_obj = tmp_dict[latest_date]['tag_commit_obj']
        print "Latest Tag in %s is: '%s'" % (self.project_name, self.latest_tag)
        print "Tag Created at: %s" % self.latest_date
        return latest_tag

    def get_commits_since(self, since, until=None):
        """
        Used date to get all commit
        e.g.
        date = '2016-08-30T12:20:16.000+08:00'
        """
        result = self.project_obj.commits.list(since=date, until=until, ref_name=self.release_branch)

        if self.detail:
            if until is None:
                print "There are {} commits in {} since {}" \
                .format(len(result), self.project_name, date)
            else:
                print "There are {} commits in {} since {} until {}" \
                .format(len(result), self.project_name, date, until)
            print "(Inculde merge request and general commit)"
        return result

    def get_commits_since_this_tag(self, tag_obj):
        tag_name = self.get_tag_detail(tag_obj, u'name')
        tag_commit_obj = self.get_tag_detail(tag_obj, u'commit')
        target_date = self.get_tag_commit_detail(tag_commit_obj, u'committed_date')

        result = []
        page = 0
        while True:
            res = self.project_obj.commits.list(since=target_date, ref_name=self.release_branch, page=page)
            if len(res) == 0:
                break
            for i in res:
                result.append(i)
            page += 1

        if self.detail:
            print
            print "===== {} =====".format(self.project_name)
            print "There are {} commits in {} since {}" \
            .format(len(result), self.project_name, tag_name)
            print "(Inculde merge request and general commit)"
        return result

    def get_commit_detail(self, commit_obj, option):
        """
        option example:
        {u'author_email': u'jiahong.wu@hopebaytech.com',
         u'author_name': u'Jiahong',
         u'created_at': u'2016-09-02T19:23:02.000+08:00',
         'gitlab': <gitlab.Gitlab at 0x103162750>,
         u'id': u'1515c82c46f11c942654daa91cb85e4545aacbed',
         u'message': u"Merge branch 'hotfix/error_handling_in_fetchcloud' into 'android-dev'\r\n\r\nError handling for unavailable download resource\r\n\r\n\r\n\r\nSee merge request !537",
         'project_id': 131,
         u'short_id': u'1515c82c',
         'since': '2016-08-30T12:20:16.000+08:00',
         u'title': u"Merge branch 'hotfix/error_handling_in_fetchcloud' into 'android-dev'\r"}
        """
        return commit_obj.as_dict()[option]

    def classify_commits(self, commits_lst):
        merge_request_dict = {}
        normal_commit_dict = {}
        feature_commits = {}
        bugfix_commits = {}
        other_commits = {}

        for commit in commits_lst:
            feature = False  # reset
            bugfix = False  # reset

            message = self.get_commit_detail(commit, 'message')
            date = self.get_commit_detail(commit, 'created_at')
            author = self.get_commit_detail(commit, 'author_name')

            # Get merge requestg
            msg = re.search(r"Merge branch \'(?P<source_branch>.+)\' into \'(?P<target_branch>.+)\'[\r\n]{2}(?P<description>.+)[\r\n]See merge request (?P<link>.+)", message, re.DOTALL)
            if message.startswith('Merge branch') and msg is not None:
                description = msg.group('description')
                while description.endswith('\r') or description.endswith('\n'):
                    description = description.replace('\r', ' ')
                    description = description.replace('\n', ' ')
                    description = description.replace('  ', '')

                source_branch = msg.group('source_branch')
                target_branch = msg.group('target_branch')
                link_number = msg.group('link')

                if 'feature' in source_branch:
                    feature = True

                if 'bug' in source_branch or 'fix' in source_branch:
                    bugfix = True

                merge_request_dict[date] = {'description': description,
                                            'source_branch': source_branch,
                                            'target_branch': target_branch,
                                            'link_number': link_number,
                                            'commit_obj': commit,
                                            'bugfix': bugfix,
                                            'feature': feature}

                if merge_request_dict[date]['feature']:
                    feature_commits[date] = merge_request_dict[date]
                elif merge_request_dict[date]['bugfix']:
                    bugfix_commits[date] = merge_request_dict[date]
                else:
                    other_commits[date] = merge_request_dict[date]

            else:
                normal_commit_dict[date] = {'message': message,
                                            'name':  author,
                                            'commit_obj': commit}
        # show number of merge request
        if self.detail:
            print '# Merge Request Number'
            print "Feature: ", len(feature_commits)
            print "Bugfix: ", len(bugfix_commits)
            print "Other: ", len(other_commits)

        return {"Normal commits": normal_commit_dict,
                "Merge requests": merge_request_dict,
                "Feature commits": feature_commits,
                "Bugfix commits": bugfix_commits,
                "Other commits": other_commits}

    def convet_message(self, commit_obj):
        """
        only accept merge_request
        """
        msg = self.release_name + ' ' + \
              commit_obj['source_branch'] + ': ' + \
              commit_obj['description'] + ' ' + \
              MarkDown.merge_request_link(self.full_link, self.project_obj, commit_obj)

        return msg

    def set_name_in_display(self, name):
        """
        e.g
        [HCFS]
        [Tera-App]
        [Tera-launcher]
        """
        self.release_name = name

    def generate_format(self, pool):
        tmp = []
        if len(pool) != 0:
            for key in pool.keys():
                msg = worker.convet_message(pool[key])
                item = MarkDown.list(msg)
                tmp.append(item)
        return tmp

    def get_changelog(self, project_name, release_branch, tag_name, name_in_changelog, full_link=True):
        self.get_project(project_name)
        self.set_name_in_display(name_in_changelog)
        self.release_branch = release_branch
        self.full_link = full_link
        target_tag_obj = self.get_tag_by_name(tag_name)
        commits = self.get_commits_since_this_tag(target_tag_obj)
        pools = self.classify_commits(commits)
        # pools = {"Normal commits": normal_commit_dict,
        #          "Merge requests": merge_request_dict,
        #          "Feature commits": feature_commits,
        #          "Bugfix commits": bugfix_commits,
        #          "Other commits": other_commits}
        self._feature_commits += self.generate_format(pools["Feature commits"])
        self._bugfix_commits += self.generate_format(pools["Bugfix commits"])
        self._other_commits += self.generate_format(pools["Other commits"])
        return pools

    def get_feature_commits(self):
        return self._feature_commits

    def get_bugfix_commits(self):
        return self._bugfix_commits

    def get_other_commits(self):
        return self._other_commits


class cfgparser:

    def __init__(self):
        self.config = ConfigParser.RawConfigParser()
        pwd = os.path.dirname(__file__)
        config_file = os.path.join(pwd, "changelog.cfg")
        self.config.read(config_file)
        self.lst = self.config.sections()
        for project in self.lst:
            setattr(self, project, atdict(self.config.items(project)))

    def projects(self):
        self.lst.remove('Gitlab')
        return self.lst


class atdict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class MarkDown(object):
    '''
    MarkDown Handler
    '''
    CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def title(string):
        """
        e.g.
        string
        =====
        """
        result = string + '\n' + '====='
        return result

    @staticmethod
    def subtitle(string, newline=False):
        """
        e.g.
        (\n) ## string
        """
        if newline:
            char = '\n'
        else:
            char = ""

        result = char + '## ' + string
        return result

    @staticmethod
    def list(string):
        """
        e.g.
        ' - string'
        """
        result = ' - ' + string
        return result

    @staticmethod
    def merge_request_link(full_link, project_obj, commit_obj):
        """
        Link in own projcet can be this format.
        (!551)
        Link from other project should be full link
        ([!551](project_group/project_name!551))

        p.s. outer "(" and ")" only decoration
        """
        if full_link:
            link = '(' + \
            '[' + commit_obj['link_number'] + ']' + '(' + \
            project_obj.path_with_namespace + \
            commit_obj['link_number'] + ')' + ')'
        else:
            link = '(' + commit_obj['link_number'] + ')'
        return link

    @staticmethod
    def repo_generate_result(md_file_path):
        with open(md_file_path, 'r') as f:
            for line in f:
                print line

    @classmethod
    def generate_md_file(cls, feature_commits, bugfix_commits, other_commits):
        tag_num = 0
        file_name = "{0}".format(sys.argv[1])
        md_file_path = os.path.join(cls.CURRENT_PATH, file_name + ".md")
        while os.path.isfile(md_file_path):
            tag_num += 1
            md_file_path = os.path.join(cls.CURRENT_PATH, "{0}-{1}.md".format(file_name, tag_num))

        with open(md_file_path, 'a') as f:
            f.writelines(cls.title(sys.argv[1]))
            f.writelines(cls.subtitle('New Features', newline=True))
            for i in feature_commits:
                f.writelines('\n' + i)

            f.writelines(cls.subtitle('Fixed', newline=True))
            for i in bugfix_commits:
                f.writelines('\n' + i)

            f.writelines(cls.subtitle('CI / Refactoring / Other', newline=True))
            for i in other_commits:
                f.writelines('\n' + i)

        cls.repo_generate_result(md_file_path)

def print_commit(commit):
    for i in commit:
        print i


cfg = cfgparser()

worker = ReleaseWorker(cfg.Gitlab.url, cfg.Gitlab.tokens)
#
# worker.detail = True # display more detail

for repo in cfg.projects():
    p = getattr(cfg, repo)
    worker.get_changelog(p.project_name, p.ref_branch,
                         p.last_release_tag, p.display_name)

# Generate result
feature_commits = worker.get_feature_commits()
bugfix_commits = worker.get_bugfix_commits()
other_commits = worker.get_other_commits()


print "## New Features"
print_commit(feature_commits)
print "## Fixed"
print_commit(bugfix_commits)
print "## CI / Refactoring / Other"
print_commit(other_commits)

print
print "=== Write to file ==="
MarkDown.generate_md_file(feature_commits, bugfix_commits, other_commits)
