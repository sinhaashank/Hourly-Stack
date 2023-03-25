# Plotting Electricity Data - EU countries

ENTSO-E, the European Network of Transmission System Operators for Electricity, is the association for the cooperation of the European transmission system operators (TSOs). The 39 member TSOs representing 35 countries are responsible for the secure and coordinated operation of Europe’s electricity system, the largest interconnected electrical grid in the world.

ENTSOE- 

Link - https://transparency.entsoe.eu/

This repository shows an example hourly of poalerting application that sends email notifications to beneficiaries in India using [COWIN platform](https://www.cowin.gov.in/home) for vaccine availability. The application interacts with the [COWIN API](https://apisetu.gov.in/public/marketplace/api/cowin) at regular intervals to find vaccination slots available at your pin code location(s) or entire district along with a minimum age limit. So, if you are currently waiting to find slots in your region and do not see any slots for your age range then, you can utilise this application to receive alerts on your email address when there are slots available for you. This way you will be able to book your appointments on time. Remember, vaccination is highly beneficial for you in this horrific time of crisis. Get your jab and protect yourself from serious illness.




Here is a sample email alert from this application containing all the required information regarding available slots:

![sample alert](https://github.com/sinhadotabhinav/covid-19-vaccine-alerts-cowin/blob/master/sample-alert.png?raw=true)

## How to run this application?

If you want to test the application and run it in foreground run:

`$ npm install && node src/app.js`

`Ctrl^C` to exit the process.

If you want to keep running the application in the background, on your terminal run:

`$ npm install && pm2 start src/app.js`

To shutdown the application run:

`$ pm2 stop src/app.js && pm2 delete src/app.js`

## Contributing

Contributions you make are greatly appreciated and always welcome. You can do so by:

1) Forking the github project
2) Creating your feature branch for example: `git checkout -b feature/my-interesting-feature`
3) Commiting your changes using `git commit -m "my-interesting-feature-update"`
4) Pushing to the branch using `git push origin feature/my-interesting-feature`
5) Finally, opening a Pull Request for review

If you would like to request a feature or report issues, please use the [Issues tracker](https://github.com/sinhadotabhinav/covid-19-vaccine-alerts-cowin/issues)

## Discussion

For any other questions or discussions, you can reach out to me via email at `sinha.ashank@gmail.com`.
