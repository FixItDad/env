PS1='${PWD}>'

PATH=$PATH:/sbin:/usr/sbin:$HOME/bin
ENV=$HOME/.aliases
export LANG=en_US.UTF-8
export LC_ALL="C"
export EDITOR=emacs

set -o emacs

# use ISO 8601 (YYYY/MM/DD HH:MM:SS format)
export LC_TIME="en_DK.UTF-8"


####SSHagent settings####
SSH_ENV="$HOME/.ssh/environment"

function start_agent {
     echo "Initializing new SSH agent..."
     /usr/bin/ssh-agent | sed 's/^echo/#echo/' > "${SSH_ENV}"
     echo succeeded
     chmod 600 "${SSH_ENV}"
     . "${SSH_ENV}" > /dev/null
#     /usr/bin/ssh-add;
}

# Source SSH settings, if applicable
if [ -f "${SSH_ENV}" ]; then
     . "${SSH_ENV}" > /dev/null
     ps -ef | grep ${SSH_AGENT_PID} | grep ssh-agent$ > /dev/null || {
         start_agent;
     }
else
     start_agent;
fi 
if [ ! $DISPLAY ] ; then
    if [ "$SSH_CLIENT" ] ; then
        export DISPLAY=`echo $SSH_CLIENT|cut -f1 -d\ `:0.0
    fi
fi
