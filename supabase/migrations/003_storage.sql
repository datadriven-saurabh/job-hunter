insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'resumes',
  'resumes',
  false,
  10485760,
  array['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','text/plain']
)
on conflict (id) do update set public = false, file_size_limit = 10485760;

insert into storage.buckets (id, name, public, file_size_limit)
values ('artifacts', 'artifacts', false, 10485760)
on conflict (id) do update set public = false, file_size_limit = 10485760;

drop policy if exists resume_owner_select on storage.objects;
create policy resume_owner_select on storage.objects for select to authenticated
using (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists resume_owner_insert on storage.objects;
create policy resume_owner_insert on storage.objects for insert to authenticated
with check (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists resume_owner_update on storage.objects;
create policy resume_owner_update on storage.objects for update to authenticated
using (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists resume_owner_delete on storage.objects;
create policy resume_owner_delete on storage.objects for delete to authenticated
using (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists artifact_owner_select on storage.objects;
create policy artifact_owner_select on storage.objects for select to authenticated
using (bucket_id = 'artifacts' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists artifact_owner_insert on storage.objects;
create policy artifact_owner_insert on storage.objects for insert to authenticated
with check (bucket_id = 'artifacts' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists artifact_owner_update on storage.objects;
create policy artifact_owner_update on storage.objects for update to authenticated
using (bucket_id = 'artifacts' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists artifact_owner_delete on storage.objects;
create policy artifact_owner_delete on storage.objects for delete to authenticated
using (bucket_id = 'artifacts' and (storage.foldername(name))[1] = auth.uid()::text);
