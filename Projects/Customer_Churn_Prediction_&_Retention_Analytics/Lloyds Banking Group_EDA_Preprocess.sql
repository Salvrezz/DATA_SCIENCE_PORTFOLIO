SELECT * from [dbo].[Customer_Churn]

--Total Customers by CustomerID
select count(distinct [CustomerID]) AS Total_Customers
from [dbo].[Customer_Churn]

--Total Customers by count on Churn_Status
select count([CustomerID]) as Total_Customers ,[ChurnStatus]
from [dbo].[Customer_Churn]
GROUP BY [ChurnStatus]

-- Total Customers with churnstatus,gender,maritalstatus,productlevel,incomelevel
SELECT
    churnstatus,
    gender,
    maritalstatus,
    productcategory AS product_level,
    incomelevel,
    COUNT(DISTINCT customerid) AS total_customers
FROM dbo.Customer_Churn
GROUP BY
    churnstatus,
    gender,
    maritalstatus,
    productcategory,
    incomelevel
ORDER BY
    churnstatus,
    gender,
    maritalstatus,
    productcategory,
    incomelevel;

--Churns Total grouped by Marital_Status
select 
    ([MaritalStatus]) ,
    count ([ChurnStatus]) as Churns
from
    [dbo].[Customer_Churn]
group by
    [MaritalStatus]

--Total Customers by Churn_Status and Marital_Status   
SELECT
    churnstatus,              -- 0 or 1
    maritalstatus,
    COUNT(DISTINCT customerid) AS total_customers
FROM dbo.vw_Customer_Churn
GROUP BY
    churnstatus,
    maritalstatus
ORDER BY
    maritalstatus,
    churnstatus;

select * from Customer_Churn

--Altering table to add AgeBracket
Begin Tran
ALTER TABLE [dbo].[Customer_Churn]
ADD AgeBracket VARCHAR(10); 
Commit

--Drop table cause of double insertion of age bracket column
Begin Tran
ALTER TABLE dbo.Customer_Churn
DROP COLUMN age_bracket;
Commit

--Updating AgeBracket column with <=18 as Young, <=50 as Adult, esle Elder
Begin Tran
UPDATE dbo.Customer_Churn
SET AgeBracket = CASE
    WHEN age <= 18 THEN 'Young'
    WHEN age <= 50 THEN 'Adult'
    ELSE 'Elder'
END;
Commit

select * from Customer_Churn

--Formating date columns 
Begin Tran
SELECT
    FORMAT(transactiondate, 'hh:mm tt') AS time_formatted
FROM dbo.vw_Customer_Churn;
Rollback


--Format all date with time column to only date
Begin Tran
ALTER TABLE dbo.Customer_Churn
ALTER COLUMN [InteractionDate] DATE;
ALTER TABLE dbo.Customer_Churn
ALTER COLUMN [TransactionDate] DATE;
ALTER TABLE dbo.Customer_Churn
ALTER COLUMN [LastLoginDate] DATE;
Commit 

select * from Customer_Churn

--
Begin Tran
SELECT
    -- 🎯 TARGET
    churnstatus,

    -- 👤 DEMOGRAPHICS
    age,
    CASE
        WHEN age <= 18 THEN 'Young'
        WHEN age <= 50 THEN 'Adult'
        ELSE 'Elder'
    END AS age_bracket,
    gender,
    maritalstatus,
    incomelevel,

    -- 🛍 PRODUCT & USAGE
    productcategory,
    amountspent,
    loginfrequency,
    serviceusage,

    -- ☎ INTERACTION FEATURES
    interactiontype,
    resolutionstatus,

    -- ⏳ TIME-BASED ENGINEERED FEATURES
    DATEDIFF(DAY, lastlogindate, GETDATE()) AS days_since_last_login,
    DATEDIFF(DAY, transactiondate, GETDATE()) AS days_since_last_transaction,
    DATEDIFF(DAY, interactiondate, GETDATE()) AS days_since_last_interaction

FROM dbo.Customer_Churn;
rollback

select * from Customer_Churn