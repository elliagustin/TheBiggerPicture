USE [tbpStaging]
GO

/****** Object:  Table [landing].[ForexMidH1]    Script Date: 25/04/2026 6:23:13 AM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE SCHEMA landing;

CREATE TABLE [landing].[ForexMidH1](
	[Datetime] [datetime] NULL,
	[Open_EURUSD] [float] NULL,
	[High_EURUSD] [float] NULL,
	[Low_EURUSD] [float] NULL,
	[Close_EURUSD] [float] NULL,
	[Volume_EURUSD] [float] NULL	
) ON [PRIMARY]
GO


