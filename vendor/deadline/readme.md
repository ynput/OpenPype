## OpenPype Deadline repository overlay

 This directory is overlay for Deadline repository. 
 It means that you can copy whole hierarchy to Deadline repository and it should work.
 
 Logic:
 -----
 Event
 -----
 For each rendering job OpenPype event is triggered, it stores path to OpenPype
 executable (needs to be configured on `Deadline's Configure Events > OpenPype`) 
 job's extra key 'openpype_executables'.
 
 This value is used by `GlobalJobPreLoad` to call that executable to pull
 environment's variables which are needed to add to ALL plugins process environments.
 These env. vars are injected into rendering process.
 
 Event is necessary here as a middle man to allow configuring location of executable
 which is ONLY then used by `GlobalJobPreLoad` (which doesnt have any user facing
 configuration at all).
 
 `GlobalJobPreLoad` is triggered before each job, it contains backward compatible
 logic to not modify old Pype2 or not OpenPype triggered jobs.
 
 Plugin
 ------
 For each publishing job `OpenPypeDeadlinePlugin` is called, which calls 
 configured location of OpenPype executable (needs to be configured in 
 `Deadline's Configure Plugins > OpenPype`) 
 and triggers command.
 
 
