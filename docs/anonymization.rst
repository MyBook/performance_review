Anonymization
~~~~~~~~~~~~~

NB: Anonymizing locally is not SECURE, goal is to make anon work in prod so that data don't leave prod.

Process is in not automated, this is algo for manual anonymizing.


1. Install https://gitlab.com/dalibo/postgresql_anonymizer locally
   https://postgresql-anonymizer.readthedocs.io/en/latest/INSTALL/#install-on-macos

2. Load production dump::

    pg_restore -d perf_real --clean --if-exists --no-owner ~/Downloads/perf.dump

3. Add security labels, defining anonymization::

    SECURITY LABEL FOR anon ON COLUMN users_user.first_name IS 'MASKED WITH FUNCTION anon.fake_first_name()';
    SECURITY LABEL FOR anon ON COLUMN users_user.last_name IS 'MASKED WITH FUNCTION anon.fake_last_name()';
    SECURITY LABEL FOR anon ON COLUMN users_user.email IS 'MASKED WITH FUNCTION anon.random_zip() || anon.fake_email()';
    SECURITY LABEL FOR anon ON COLUMN users_user.username IS 'MASKED WITH FUNCTION anon.random_zip() || anon.fake_email()';
    SECURITY LABEL FOR anon ON COLUMN users_user.name IS 'MASKED WITH VALUE ''''';
    SECURITY LABEL FOR anon ON COLUMN users_user.avatar IS 'MASKED WITH VALUE ''''';
    SECURITY LABEL FOR anon ON COLUMN users_user.password IS 'MASKED WITH VALUE ''''';
    SECURITY LABEL FOR anon ON COLUMN reviews_job.name IS 'MASKED WITH FUNCTION anon.fake_company() || '' '' || anon.random_zip()';
    SECURITY LABEL FOR anon ON COLUMN users_department.name IS 'MASKED WITH FUNCTION anon.fake_region() || '' '' || anon.random_zip()';
    SECURITY LABEL FOR anon ON COLUMN reviews_selfreview.text IS 'MASKED WITH FUNCTION anon.lorem_ipsum(2)';
    SECURITY LABEL FOR anon ON COLUMN reviews_selfreview.comment IS 'MASKED WITH FUNCTION anon.lorem_ipsum( words := 20 )';
    SECURITY LABEL FOR anon ON COLUMN reviews_review.text IS 'MASKED WITH FUNCTION anon.lorem_ipsum(2)';
    SECURITY LABEL FOR anon ON COLUMN reviews_review.comment IS 'MASKED WITH FUNCTION anon.lorem_ipsum( words := 20 )';
    SECURITY LABEL FOR anon ON COLUMN reviews_review.score IS 'MASKED WITH FUNCTION anon.random_int_between(1,5)';
    SECURITY LABEL FOR anon ON COLUMN django_site.domain IS 'MASKED WITH VALUE ''example''';
 
4. Make sure labels are created (typos didn't prevent labels creation)::

    SELECT * FROM pg_seclabels;
    
5. Delete data that can't be anonymized and not required or can be easily recreated manually::

    DELETE FROM account_emailaddress;
    DELETE FROM account_emailconfirmation;
    DELETE FROM auth_group;
    DELETE FROM auth_group_permissions;
    DELETE FROM goals_goal;
    DELETE FROM django_admin_log;
    DELETE FROM django_session;
    DELETE FROM reviews_role;
    DELETE FROM socialaccount_socialtoken;
    DELETE FROM socialaccount_socialaccount;
    DELETE FROM socialaccount_socialapp_sites;
    DELETE FROM socialaccount_socialapp;
    DELETE FROM users_user_groups;
    DELETE FROM users_user_user_permissions;

6. Check and update anonymization report manually checking results!
   (use \dt to get table list, fill status using SELECT * FROM table)::

    Schema  |                 Name                 | Anonymized
    --------+--------------------------------------+-----------------
     public | account_emailaddress                 | Deleted
     public | account_emailconfirmation            | Deleted
     public | auth_group                           | Deleted
     public | auth_group_permissions               | Deleted
     public | auth_permission                      | OK
     public | django_admin_log                     | Deleted
     public | django_content_type                  | OK
     public | django_migrations                    | OK
     public | django_session                       | Deleted
     public | django_site                          | Anonymized
     public | goals_goal                           | Deleted
     public | reviews_interval                     | OK
     public | reviews_job                          | Anonymized
     public | reviews_review                       | Anonymized
     public | reviews_role                         | Deleted
     public | reviews_selfreview                   | Anonymized
     public | socialaccount_socialaccount          | Deleted
     public | socialaccount_socialapp              | Deleted
     public | socialaccount_socialapp_sites        | Deleted
     public | socialaccount_socialtoken            | Deleted
     public | users_department                     | Anonymized
     public | users_user                           | Anonymized
     public | users_user_groups                    | Deleted
     public | users_user_user_permissions          | Deleted

7. create superuser admin:admin for development::

    python manage.py createsuperuser

    http://localhost:8000/admin/
