var plan = require('flightplan');


// configuration
plan.target('deploy', {
    host: 'fit-demo-dev',
    username: 'pi',
    agent: process.env.SSH_AUTH_SOCK
});


// run commands on localhost
// plan.local(function(local) {
// });


// run commands on remote hosts
plan.remote(function(remote) {

    remote.with('cd ~/demo/dashboard/', function() {
        // remote.ls('-l');
        remote.log('=== Update remote repository');
        remote.exec('git pull')

        remote.log('=== Update node dependencies');
        remote.exec('git diff-tree -r --name-only --no-commit-id HEAD@{1} HEAD | grep --quiet "package.json" && eval "npm install"') // run 'npm install' when package.json has changed
    });
    
});