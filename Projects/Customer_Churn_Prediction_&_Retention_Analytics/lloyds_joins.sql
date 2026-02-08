select * from Churn_Status$;


select * from Customer_Demographics$;

select * from Customer_Service$;

select * from Online_Activity$;

select * from Transaction_History$;

--Join Tables Using CustomerID as Unique key in a tables
CREATE VIEW dbo.vw_Customer_Churn AS 
SELECT
    cc.CustomerID,
    cc.ChurnStatus,
    cs.InteractionID,
    cs.InteractionDate,
    cs.InteractionType,
    cs.ResolutionStatus,
    ts.TransactionID,
    ts.TransactionDate,
    ts.AmountSpent,
    ts.ProductCategory,
    cd.Age,
    cd.Gender,
    cd.MaritalStatus,
    cd.IncomeLevel,
    oa.LastLoginDate,
    oa.LoginFrequency,
    oa.ServiceUsage
FROM Churn_Status$ as cc
LEFT JOIN  Customer_Service$ cs
    ON cc.CustomerID = cs.CustomerID
LEFT JOIN Transaction_History$ as ts
    ON cc.CustomerID = ts.CustomerID
LEFT JOIN  Customer_Demographics$ as cd
    ON cc.CustomerID = cd.CustomerID
LEFT JOIN Online_Activity$ oa
    ON cc.CustomerID = oa.CustomerID;

--Display Total_Customers 
Begin TRAN
SELECT COUNT(DISTINCT CustomerID) AS TotalCustomers
FROM (
    SELECT cc.CustomerID
    FROM Churn_Status$ cc
    LEFT JOIN Customer_Service$ cs ON cc.CustomerID = cs.CustomerID
    LEFT JOIN Transaction_History$ ts ON cc.CustomerID = ts.CustomerID
    LEFT JOIN Customer_Demographics$ cd ON cc.CustomerID = cd.CustomerID
    LEFT JOIN Online_Activity$ oa ON cc.CustomerID = oa.CustomerID) t;
COMMIT


SELECT *
INTO Customer_Churn
FROM vw_Customer_Churn;
