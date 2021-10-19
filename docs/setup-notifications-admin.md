# How to setup Notifications Admin

ℹ️ **Before running through the steps below, please ensure you've completed all the steps in our [Setup Python Dev Environment](./setup-python-dev-environment.md) documentation.**

## Downloading the `notifications-admin` application

First, let's clone the notifications-admin codebase from GitHub:

```
git clone git@github.com:bitzesty/notifications-admin.git
```

Next, let's use the `virtualenv` tool to create a new (virtual) environment into which our Python dependencies will be installed. Using `virtualenv` allows us to keep our dependencies separate between Python projects, removing any chance of conflicts across different applications.

```
virtualenv env
source env/bin/activate
```

ℹ️ **It's important to note that you'll need to run the above `activate` command each time you `cd` into a project's codebase.**

## Installing Node.js

The notifications-admin application uses the node package manager (`npm`) to install and update front-end dependencies. To gain access to `npm` we must install `Node.js`. Please visit the [official Node.js download page](https://nodejs.org/en/download/) to download and install `Node.js` for your operating system.

## Bootstrapping the `notifications-admin` application for local development
Next, we can install dependencies, configuring our local development environment with minimal fuss and effort.
```
make bootstrap
```

## How to run the application

Once you've completed the steps above, you're ready to run the admin app locally.  

Since the `notifications-admin` app is a front-end to the `notifications-api` app, you'll need to have the `notifications-api` app running in another terminal window.  

Once `notifications-api` is running and listening on port 6011, we can start `notifications-admin` on port 6012 using this command.

```
make run-flask
```

You should be able to view the `notifications-admin` app on http://localhost:6012

![notifications-admin app running on localhpost:6012](images/localhost-notifications-admin.png)


